from fastapi import FASAPI,HTTPExecution, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import uvicorn 

from config.settings import settings
from app.database import DatabaseManager
from app.api.auth.auth import AuthService, get_current_active_user
from app.models.models import User

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {settings.app}")
    await DatabasseManager.init_db()
    print("database initialized")
    yield

    print("Shutting down")

    
app = FastAPI(
    Title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

from pydantic import BaseModel, EMAILStr
from datetime import timedelta

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@app.post("/api/auth/register", response_model=dict)
async def register(
    user_data: dict,
    db = Depends(get_async_db)
):
    existing_user= await AuthService.get_user_by_email(db, user_data["email"])
    if exting_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    new_user = await AuthService.create_user(
        db=db,
        email=user_data["email"],
        username=user_data["username"],
        full_name=user_data["full_name"],
        password=user_data["password"],
        user_type=user_data["user_type", "student"]
    )
    return{
    "message": "User created successifully",
    "user_id": new_user.id,
    "email": new_user.email
    }

@app.post("/api/auth/login")
async def login(
    login_data: LoginRequest,
    db = Depends(get_async_db)
):
    user = await AuthService.authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = AuthService.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "user_type": user.user_type,
            "is_premium": user.is_premium
        }
    }

@app.get("/api/auth/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user's profile information
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "user_type": current_user.user_type,
        "is_premium": current_user.is_premium,
        "created_at": current_user.created_at
    }

@app.get("/")
async def root():
    """
    Basic health check endpoint
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "status": "healthy"
    }

@app.get("/api/health")
async def health_check():
    """
    Detailed health check for monitoring
    """
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": settings.version,
        "database": "connected", 
        "redis": "connected"      
    }


from app.models.models import Essay, EssayGrading
from sqlalchemy import select
from app.database import get_async_db

class EssaySubmission(BaseModel):
    title: str
    content: str
    task_type: str = "general"  

@app.post("/api/essays/submit")
async def submit_essay(
    essay_data: EssaySubmission,
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_async_db)
):
    
    word_count = len(essay_data.content.split())

    new_essay = Essay(
        title=essay_data.title,
        content=essay_data.content,
        task_type=essay_data.task_type,
        word_count=word_count,
        author_id=current_user.id
    )
    
    db.add(new_essay)
    await db.commit()
    await db.refresh(new_essay)
    
    # TODO: Queue for AI grading (we'll add this with Celery)
    
    return {
        "message": "Essay submitted successfully",
        "essay_id": new_essay.id,
        "word_count": word_count,
        "status": "submitted"
    }

@app.get("/api/essays/my-essays")
async def get_my_essays(
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_async_db)
):
    """
    Get all essays submitted by the current user
    """
    result = await db.execute(
        select(Essay).where(Essay.author_id == current_user.id).order_by(Essay.submitted_at.desc())
    )
    essays = result.scalars().all()
    
    return {
        "essays": [
            {
                "id": essay.id,
                "title": essay.title,
                "task_type": essay.task_type,
                "word_count": essay.word_count,
                "is_graded": essay.is_graded,
                "overall_score": essay.overall_score,
                "submitted_at": essay.submitted_at
            }
            for essay in essays
        ]
    }

@app.get("/api/essays/{essay_id}")
async def get_essay_details(
    essay_id: int,
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_async_db)
):
    
    result = await db.execute(
        select(Essay).where(Essay.id == essay_id, Essay.author_id == current_user.id)
    )
    essay = result.scalar_one_or_none()
    
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")
    
    grading_result = None
    if essay.is_graded:
        grading_query = await db.execute(
            select(EssayGrading).where(EssayGrading.essay_id == essay_id)
        )
        grading = grading_query.scalar_one_or_none()
        if grading:
            grading_result = {
                "overall_band": grading.overall_band,
                "task_achievement": grading.task_achievement,
                "coherence_cohesion": grading.coherence_cohesion,
                "lexical_resource": grading.lexical_resource,
                "grammar_accuracy": grading.grammar_accuracy,
                "feedback": grading.feedback,
                "ai_model_used": grading.ai_model_used,
                "created_at": grading.created_at
            }
    
    return {
        "essay": {
            "id": essay.id,
            "title": essay.title,
            "content": essay.content,
            "task_type": essay.task_type,
            "word_count": essay.word_count,
            "submitted_at": essay.submitted_at,
            "graded_at": essay.graded_at
        },
        "grading": grading_result
    }


from app.models.models import SpeakingTask, SpeakingAnalysis
from fastapi import UploadFile, File
import aiofiles
import os

@app.post("/api/speaking/submit")
async def submit_speaking_task(
    audio_file: UploadFile = File(...),
    task_type: str = "part1",
    question: str = "",
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_async_db)
):
    
    if not audio_file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be audio format")
    
    upload_dir = settings.upload_folder
    os.makedirs(upload_dir, exist_ok=True)
    
    import uuid
    file_extension = audio_file.filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await audio_file.read()
        await f.write(content)
    
    # TODO: Get audio duration (we'll add this later)
    
    speaking_task = SpeakingTask(
        user_id=current_user.id,
        audio_filename=unique_filename,
        task_type=task_type,
        question=question
    )
    
    db.add(speaking_task)
    await db.commit()
    await db.refresh(speaking_task)
    
    # TODO: Queue for AI analysis (we'll add this with Celery)
    
    return {
        "message": "Audio submitted successfully",
        "task_id": speaking_task.id,
        "status": "submitted"
    }

@app.get("/api/speaking/my-tasks")
async def get_my_speaking_tasks(
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_async_db)
):
    """
    Get all speaking tasks submitted by the current user
    """
    result = await db.execute(
        select(SpeakingTask).where(SpeakingTask.user_id == current_user.id).order_by(SpeakingTask.submitted_at.desc())
    )
    tasks = result.scalars().all()
    
    return {
        "tasks": [
            {
                "id": task.id,
                "task_type": task.task_type,
                "question": task.question,
                "audio_duration": task.audio_duration,
                "is_analyzed": task.is_analyzed,
                "submitted_at": task.submitted_at
            }
            for task in tasks
        ]
    }


@app.get("/api/admin/stats")
async def get_admin_stats(
    current_user: User = Depends(get_current_admin),
    db = Depends(get_async_db)
):
    
    user_count_result = await db.execute(select(func.count(User.id)))
    total_users = user_count_result.scalar()
    
    essay_count_result = await db.execute(select(func.count(Essay.id)))
    total_essays = essay_count_result.scalar()
    
    speaking_count_result = await db.execute(select(func.count(SpeakingTask.id)))
    total_speaking_tasks = speaking_count_result.scalar()
    
    return {
        "total_users": total_users,
        "total_essays": total_essays,
        "total_speaking_tasks": total_speaking_tasks,
        "app_version": settings.version
    }

from sqlalchemy import func

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.debug else False
    )