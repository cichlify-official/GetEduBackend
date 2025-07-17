from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import os

from config.settings import settings
from app.database import init_db, get_db, check_db_health, close_db
from app.api.auth.auth import AuthService, UserCreate, UserLogin, Token, get_current_active_user
from app.models.models import User

# Import all routers
from app.api.routes.essays import router as essays_router
from app.api.routes.ai_grading import router as ai_router
from app.api.routes.speaking import router as speaking_router
from app.api.routes.admin import router as admin_router
from app.api.routes.dashboard import router as dashboard_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Starting {settings.app_name}")
    
    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        # Don't raise, let the app start anyway for health checks
    
    # Create upload directory
    try:
        os.makedirs(settings.upload_folder, exist_ok=True)
        logger.info(f"📁 Upload folder ready: {settings.upload_folder}")
    except Exception as e:
        logger.warning(f"Could not create upload folder: {e}")
    
    yield
    
    # Cleanup
    logger.info("👋 Shutting down gracefully")
    try:
        await close_db()
    except Exception as e:
        logger.error(f"Error closing database: {e}")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Complete IELTS AI Learning Platform - Reading, Listening, Writing, Speaking & AI Curriculum",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware - allow all for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers for available features
app.include_router(essays_router)           # Writing essays
app.include_router(ai_router)               # AI grading
app.include_router(speaking_router)         # Speaking practice
app.include_router(admin_router)            # Admin features
app.include_router(dashboard_router)        # User dashboard

# --- BASIC ROUTES ---
@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "status": "running",
        "environment": "production" if not settings.debug else "development",
        "features": [
            "🎯 AI-Powered Learning",
            "✍️ Writing Analysis",
            "🎤 Speaking Assessment",
            "📊 Progress Tracking",
            "🤖 Personalized Learning"
        ],
        "endpoints": {
            "authentication": "/api/auth",
            "writing": "/api/essays",
            "speaking": "/api/speaking",
            "dashboard": "/api/dashboard",
            "admin": "/api/admin"
        },
        "ai_enabled": bool(settings.openai_api_key and settings.openai_api_key.startswith("sk-")),
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    try:
        db_healthy = await check_db_health()
    except Exception as e:
        logger.error(f"Health check database error: {e}")
        db_healthy = False
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "ai": "available" if settings.openai_api_key else "unavailable",
        "app": settings.app_name,
        "version": settings.version,
        "features": {
            "writing": "active",
            "speaking": "active",
            "ai_grading": "active"
        }
    }

# --- AUTHENTICATION ROUTES ---
@app.post("/api/auth/register", response_model=dict)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    try:
        existing_user = await AuthService.get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        new_user = await AuthService.create_user(db, user_data)
        
        return {
            "message": "User created successfully",
            "user_id": new_user.id,
            "email": new_user.email,
            "username": new_user.username,
            "welcome_message": "Welcome to the IELTS AI Learning Platform! 🎓"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/api/auth/login", response_model=Token)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login user and return JWT token"""
    try:
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
                "full_name": user.full_name,
                "username": user.username
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user profile"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "user_type": current_user.user_type,
        "created_at": current_user.created_at.isoformat(),
        "platform_features": [
            "Writing Analysis with AI Grading",
            "Speaking Assessment and Feedback",
            "Progress Tracking and Analytics",
            "Personalized Learning Experience"
        ]
    }

# --- DEMO & TEST ROUTES ---
@app.get("/api/demo/protected")
async def protected_demo(current_user: User = Depends(get_current_active_user)):
    return {
        "message": f"Hello {current_user.full_name}! Welcome to the IELTS AI platform.",
        "user_id": current_user.id,
        "user_type": current_user.user_type,
        "available_features": [
            "✍️ AI-powered writing analysis",
            "🎤 Speaking assessment and tips",
            "📊 Detailed progress tracking",
            "🤖 Personalized learning recommendations"
        ]
    }

@app.get("/api/features")
async def get_platform_features():
    """Get all available platform features"""
    return {
        "writing": {
            "description": "AI-powered essay analysis",
            "features": ["AI grading", "Band scoring", "Grammar analysis", "Improvement suggestions"],
            "endpoint": "/api/essays"
        },
        "speaking": {
            "description": "Speaking assessment and practice",
            "features": ["Audio recording", "Fluency analysis", "Pronunciation feedback", "Part-specific tips"],
            "endpoint": "/api/speaking"
        },
        "dashboard": {
            "description": "Progress and performance tracking",
            "features": ["Skill breakdown", "Band prediction", "Study statistics", "Achievement tracking"],
            "endpoint": "/api/dashboard"
        },
        "ai_grading": {
            "description": "Advanced AI analysis",
            "features": ["Free AI grading", "Detailed feedback", "IELTS band scoring", "Writing improvement tips"],
            "endpoint": "/api/ai"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)