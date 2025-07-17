from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import os

from config.settings import settings
from app.database import init_db, get_db
from app.api.auth.auth import AuthService, UserCreate, UserLogin, Token, get_current_active_user
from app.models.models import User

# Import all routers
from app.api.routes.essays import router as essays_router
from app.api.routes.ai_grading import router as ai_grading_router
from app.api.routes.speaking import router as speaking_router
from app.api.routes.admin import router as admin_router
from app.api.routes.dashboard import router as dashboard_router

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Starting {settings.app_name} - GET Education Platform")
    await init_db()
    print("✅ Database initialized")
    print("🎯 All language skills supported: Writing, Speaking, Reading, Listening")
    print("📚 AI-powered grading and lesson planning ready")
    yield
    print("👋 Shutting down GET Education Platform")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="""
    GET Education Platform - AI-powered language learning assessment system
    
    �� **Features:**
    - **Writing Assessment**: IELTS-style essay grading with detailed feedback
    - **Speaking Analysis**: Audio transcription and pronunciation evaluation
    - **AI Integration**: OpenAI GPT-4 for intelligent grading and feedback
    - **Multi-role Support**: Students, Teachers, and Administrators
    - **Progress Tracking**: Comprehensive analytics and learning recommendations
    
    🔧 **AI Integration:**
    - OpenAI GPT-4 for intelligent grading and feedback
    - Whisper for audio transcription
    - Free fallback AI service for demo usage
    
    🏫 **Educational Focus:**
    - IELTS/TOEFL preparation
    - General English proficiency
    - Skills-based learning approach
    - Progress tracking and analytics
    """,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (for audio files, etc.)
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include all routers
app.include_router(essays_router)
app.include_router(ai_grading_router)
app.include_router(speaking_router)
app.include_router(admin_router)
app.include_router(dashboard_router)

# --- ROOT ROUTES ---
@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name} - GET Education Platform",
        "tagline": "AI-powered language learning assessment by Cichlify",
        "version": settings.version,
        "status": "running",
        "features": {
            "writing": "IELTS-style essay grading and feedback",
            "speaking": "Audio transcription and pronunciation analysis",
            "ai_integration": "GPT-4 powered grading with free fallback",
            "progress_tracking": "Comprehensive learning analytics",
            "multi_role": "Students, Teachers, and Administrators"
        },
        "supported_roles": ["student", "teacher", "admin"],
        "ai_enabled": bool(settings.openai_api_key and settings.openai_api_key.startswith("sk-")),
        "endpoints": {
            "authentication": "/api/auth/*",
            "writing": "/api/essays/* and /api/ai/*",
            "speaking": "/api/speaking/*",
            "dashboard": "/api/dashboard/*",
            "admin": "/api/admin/*",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "platform": "GET Education",
        "database": "connected",
        "ai_service": "available" if settings.openai_api_key else "demo_mode",
        "features": {
            "writing_assessment": "active",
            "speaking_analysis": "active",
            "progress_tracking": "active",
            "admin_panel": "active"
        }
    }

# --- AUTHENTICATION ROUTES ---
@app.post("/api/auth/register", response_model=dict)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user (student, teacher, or admin)"""
    existing_user = await AuthService.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = await AuthService.create_user(db, user_data)
    
    return {
        "message": "User created successfully",
        "user_id": new_user.id,
        "email": new_user.email,
        "username": new_user.username,
        "user_type": new_user.user_type.value,
        "platform": "GET Education"
    }

@app.post("/api/auth/login", response_model=Token)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login user and return JWT token"""
    user = await AuthService.authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = AuthService.create_access_token(
        data={"sub": user.email, "user_type": user.user_type.value}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "user_type": user.user_type.value
        }
    }

@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user profile"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "user_type": current_user.user_type.value,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
        "platform": "GET Education"
    }

# --- DEMO ROUTES ---
@app.get("/api/demo/protected")
async def protected_demo(current_user: User = Depends(get_current_active_user)):
    return {
        "message": f"Hello {current_user.full_name}! This is a protected endpoint.",
        "user_id": current_user.id,
        "user_type": current_user.user_type.value
    }

@app.get("/api/platform/stats")
async def get_platform_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get platform usage statistics"""
    from sqlalchemy import func
    
    # Get counts
    essay_count = await db.execute(select(func.count(Essay.id)))
    user_count = await db.execute(select(func.count(User.id)))
    
    return {
        "platform": "GET Education",
        "statistics": {
            "total_users": user_count.scalar(),
            "total_essays": essay_count.scalar(),
            "ai_powered_features": [
                "Automated essay grading",
                "Audio transcription and analysis",
                "Progress tracking and analytics",
                "Personalized learning recommendations"
            ]
        },
        "user_type": current_user.user_type.value,
        "generated_at": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
