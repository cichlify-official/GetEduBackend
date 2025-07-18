# app/main.py - MVP version that WILL work
import os
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import FastAPI
from app.api.routes import evaluation


app = FastAPI()
app.include_router(evaluation.router)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Settings
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# In-memory storage for MVP (will be replaced with database later)
users_db = {}
essays_db = {}
user_counter = 1
essay_counter = 1

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class EssayCreate(BaseModel):
    title: str
    content: str
    task_type: str = "general"

class User(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    hashed_password: str
    created_at: str

# Auth functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def get_user_by_email(email: str) -> Optional[User]:
    for user in users_db.values():
        if user["email"] == email:
            return User(**user)
    return None

def authenticate_user(email: str, password: str) -> Optional[User]:
    user = get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_email(email=email)
    if user is None:
        raise credentials_exception
    return user

# Create FastAPI app
app = FastAPI(
    title="Language Learning AI Backend - MVP",
    version="1.0.0",
    description="Minimal viable product for language learning AI"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("🚀 Language Learning AI Backend MVP Started!")

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0-mvp",
        "database": "in-memory",
        "ai": "configured" if OPENAI_API_KEY else "not_configured",
        "users_count": len(users_db),
        "essays_count": len(essays_db)
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Language Learning AI Backend MVP",
        "version": "1.0.0-mvp",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "features": ["Authentication", "Essay Management", "AI Grading (Free)"]
    }

# Authentication endpoints
@app.post("/api/auth/register")
async def register(user_data: UserCreate):
    global user_counter
    
    # Check if user exists
    if get_user_by_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = {
        "id": user_counter,
        "email": user_data.email,
        "username": user_data.username,
        "full_name": user_data.full_name,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow().isoformat()
    }
    
    users_db[user_counter] = user
    user_counter += 1
    
    logger.info(f"User registered: {user_data.email}")
    
    return {
        "message": "User created successfully",
        "user_id": user["id"],
        "email": user["email"],
        "username": user["username"]
    }

@app.post("/api/auth/login", response_model=Token)
async def login(login_data: UserLogin):
    user = authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    logger.info(f"User logged in: {user.email}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name
        }
    }

@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "created_at": current_user.created_at
    }

# Essay endpoints
@app.post("/api/essays/submit")
async def submit_essay(essay_data: EssayCreate, current_user: User = Depends(get_current_user)):
    global essay_counter
    
    word_count = len(essay_data.content.split())
    
    essay = {
        "id": essay_counter,
        "title": essay_data.title,
        "content": essay_data.content,
        "task_type": essay_data.task_type,
        "word_count": word_count,
        "author_id": current_user.id,
        "author_username": current_user.username,
        "is_graded": False,
        "overall_score": None,
        "submitted_at": datetime.utcnow().isoformat()
    }
    
    essays_db[essay_counter] = essay
    essay_counter += 1
    
    logger.info(f"Essay submitted by {current_user.username}: {essay_data.title}")
    
    return {
        "message": "Essay submitted successfully",
        "essay_id": essay["id"],
        "word_count": word_count,
        "status": "submitted"
    }

@app.get("/api/essays/my-essays")
async def get_my_essays(current_user: User = Depends(get_current_user)):
    user_essays = [essay for essay in essays_db.values() if essay["author_id"] == current_user.id]
    
    return {
        "essays": [
            {
                "id": essay["id"],
                "title": essay["title"],
                "task_type": essay["task_type"],
                "word_count": essay["word_count"],
                "is_graded": essay["is_graded"],
                "overall_score": essay["overall_score"],
                "submitted_at": essay["submitted_at"]
            }
            for essay in sorted(user_essays, key=lambda x: x["submitted_at"], reverse=True)
        ]
    }

@app.get("/api/essays/{essay_id}")
async def get_essay_details(essay_id: int, current_user: User = Depends(get_current_user)):
    essay = essays_db.get(essay_id)
    if not essay or essay["author_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="Essay not found")
    
    return {
        "essay": {
            "id": essay["id"],
            "title": essay["title"],
            "content": essay["content"],
            "task_type": essay["task_type"],
            "word_count": essay["word_count"],
            "submitted_at": essay["submitted_at"]
        },
        "grading": essay.get("grading")
    }

# Free AI grading (rule-based)
@app.post("/api/ai/demo-grade")
async def demo_grade_text(text_data: dict, current_user: User = Depends(get_current_user)):
    content = text_data.get("content", "")
    task_type = text_data.get("task_type", "general")

    if not content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    # -- ✨ NEW AI GRADING LOGIC USING OPENAI API --
    import openai
    openai.api_key = OPENAI_API_KEY

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an IELTS writing examiner. You give honest, structured, and helpful feedback."
                },
                {
                    "role": "user",
                    "content": f"""Please grade this IELTS Task 2 essay on a scale of 0–9 for:
- Task Achievement
- Coherence and Cohesion
- Lexical Resource
- Grammatical Range and Accuracy

Then give:
- A summary of strengths
- A list of weaknesses
- 3 personalized recommendations

Essay:
\"\"\"
{content}
\"\"\"
"""
                }
            ],
            temperature=0.7
        )

        result = response['choices'][0]['message']['content']

        return {
            "message": "AI grading completed",
            "analysis_type": "gpt4",
            "grading": result,
            "cost": "OpenAI API used"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Speaking demo endpoint
@app.post("/api/speaking/demo-analyze")
async def demo_speaking_analysis(text_data: dict, current_user: User = Depends(get_current_user)):
    text = text_data.get("text", "")
    
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    word_count = len(text.split())
    
    # Simple speaking analysis
    scores = {
        "fluency_coherence": 6.5,
        "lexical_resource": 6.0,
        "grammatical_range": 6.0,
        "pronunciation": 6.5,
        "overall_band": 6.3
    }
    
    return {
        "message": "Speaking analysis completed (demo)",
        "scores": scores,
        "analysis": {
            "word_count": word_count,
            "estimated_duration": f"{word_count / 150:.1f} minutes"
        },
        "feedback": {
            "strengths": ["Good attempt at speaking"],
            "improvements": ["Continue practicing fluency"],
            "suggestions": ["Record yourself more often"]
        }
    }

# Admin endpoint
@app.get("/api/admin/stats")
async def get_admin_stats(current_user: User = Depends(get_current_user)):
    return {
        "platform_stats": {
            "total_users": len(users_db),
            "total_essays": len(essays_db),
            "graded_essays": sum(1 for essay in essays_db.values() if essay["is_graded"]),
            "system_type": "MVP In-Memory"
        },
        "recent_activity": [
            {
                "type": "essay_submission",
                "user": essay["author_username"],
                "title": essay["title"],
                "time": essay["submitted_at"]
            }
            for essay in sorted(essays_db.values(), key=lambda x: x["submitted_at"], reverse=True)[:5]
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:main", host="0.0.0.0", port=port)
