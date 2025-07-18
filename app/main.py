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
from app.api.routes.essays import router as essays_router
from app.api.routes.speaking import router as speaking_router
from app.api.routes.admin import router as admin_router
from app.api.routes.dashboard import router as dashboard_router
from app.models.models import User

# Import enhanced routes
from app.api.routes.ai_grading import router as enhanced_ai_router
from app.api.routes.speaking import router as enhanced_speaking_router

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Starting {settings.app_name}")
    print("🔧 Initializing database...")
    await init_db()
    
    # Create uploads directory
    os.makedirs("uploads", exist_ok=True)
    print("📁 Upload directory ready")
    
    # Check AI service availability
    ai_status = "✅ Enhanced Free AI Service" if settings.openai_api_key else "⚡ Free Rule-Based AI Service"
    print(f"🤖 AI Service: {ai_status}")
    
    print("✅ Application startup complete!")
    yield
    print("👋 Shutting down gracefully")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI-powered language learning platform with comprehensive evaluation and personalized improvement courses",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (for frontend)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(essays_router)
app.include_router(enhanced_ai_router)  # Enhanced AI grading
app.include_router(enhanced_speaking_router)  # Enhanced speaking analysis
app.include_router(admin_router)
app.include_router(dashboard_router)

# --- ROOT ROUTES ---
@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "status": "running",
        "features": [
            "✅ User Authentication",
            "✅ Essay Submission & Evaluation", 
            "✅ Speaking Analysis",
            "✅ Comprehensive AI Feedback",
            "✅ Personalized Improvement Courses",
            "✅ Progress Tracking",
            "✅ Strengths & Weaknesses Analysis"
        ],
        "ai_service": "Enhanced Free AI Service" if settings.openai_api_key else "Free Rule-Based AI Service",
        "cost": "100% Free",
        "endpoints": {
            "auth": "/api/auth/",
            "essays": "/api/essays/", 
            "ai_evaluation": "/api/ai/",
            "speaking": "/api/speaking/",
            "dashboard": "/api/dashboard/",
            "admin": "/api/admin/",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "ai_service": "available",
        "features": "all_operational",
        "version": settings.version
    }

# --- AUTHENTICATION ROUTES ---
@app.post("/api/auth/register", response_model=dict)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    existing_user = await AuthService.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = await AuthService.create_user(db, user_data)
    
    return {
        "message": "User created successfully",
        "user_id": new_user.id,
        "email": new_user.email,
        "username": new_user.username,
        "welcome_message": f"Welcome to {settings.app_name}! Start by submitting your first essay or speaking task."
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
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
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
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user profile"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "user_type": current_user.user_type,
        "created_at": current_user.created_at.isoformat(),
        "account_status": "active"
    }

# --- DEMO ROUTES ---
@app.get("/api/demo/protected")
async def protected_demo(current_user: User = Depends(get_current_active_user)):
    return {
        "message": f"Hello {current_user.full_name}! This is a protected endpoint.",
        "user_id": current_user.id,
        "user_type": current_user.user_type,
        "available_features": [
            "Essay Writing & Evaluation",
            "Speaking Practice & Analysis", 
            "Progress Tracking",
            "Personalized Improvement Courses",
            "Comprehensive Feedback"
        ]
    }

@app.get("/api/demo/features")
async def demo_features():
    """Demo endpoint showing available features"""
    return {
        "platform_features": {
            "writing_evaluation": {
                "description": "Comprehensive essay analysis with IELTS-style scoring",
                "features": [
                    "Task Achievement scoring",
                    "Coherence & Cohesion analysis",
                    "Lexical Resource evaluation",
                    "Grammar & Accuracy checking",
                    "Detailed feedback with strengths/weaknesses"
                ]
            },
            "speaking_analysis": {
                "description": "Video/audio recording with AI-powered speaking evaluation",
                "features": [
                    "Fluency & Coherence assessment",
                    "Pronunciation analysis",
                    "Vocabulary usage evaluation",
                    "Grammar in speech evaluation",
                    "Personalized speaking tips"
                ]
            },
            "improvement_courses": {
                "description": "Personalized learning paths based on your performance",
                "features": [
                    "Skill-specific improvement plans",
                    "Weekly study schedules",
                    "Daily practice activities",
                    "Progress milestones",
                    "Estimated improvement timelines"
                ]
            },
            "progress_tracking": {
                "description": "Monitor your improvement over time",
                "features": [
                    "Score history tracking",
                    "Skill-specific progress charts",
                    "Improvement trends analysis",
                    "Personalized recommendations",
                    "Achievement milestones"
                ]
            }
        },
        "ai_technology": {
            "type": "Enhanced Free AI Service",
            "cost": "100% Free",
            "accuracy": "High-quality rule-based analysis",
            "features": [
                "Instant feedback",
                "Detailed error analysis",
                "Personalized recommendations",
                "Comprehensive scoring",
                "Improvement course generation"
            ]
        }
    }

# --- QUICK START GUIDE ---
@app.get("/api/quick-start")
async def quick_start_guide():
    """Quick start guide for new users"""
    return {
        "welcome": "Welcome to GetEdu - Your AI Language Learning Partner!",
        "quick_start_steps": [
            {
                "step": 1,
                "title": "Register & Login",
                "description": "Create your account to start tracking progress",
                "endpoint": "/api/auth/register"
            },
            {
                "step": 2,
                "title": "Submit Your First Essay",
                "description": "Write an essay and get comprehensive AI feedback",
                "endpoint": "/api/essays/submit"
            },
            {
                "step": 3,
                "title": "Get AI Evaluation",
                "description": "Receive detailed analysis with strengths and weaknesses",
                "endpoint": "/api/ai/evaluate-essay"
            },
            {
                "step": 4,
                "title": "Try Speaking Practice",
                "description": "Record yourself speaking and get pronunciation feedback",
                "endpoint": "/api/speaking/analyze-speaking"
            },
            {
                "step": 5,
                "title": "Follow Your Improvement Course",
                "description": "Get personalized study plan based on your performance",
                "endpoint": "/api/ai/improvement-course"
            }
        ],
        "tips": [
            "Start with shorter essays (150-200 words) to get comfortable",
            "Practice speaking for 1-2 minutes on familiar topics",
            "Review your feedback carefully and focus on weak areas",
            "Use the improvement course to guide your study",
            "Track your progress over time to stay motivated"
        ],
        "sample_topics": {
            "writing": [
                "Describe your hometown",
                "Advantages and disadvantages of social media",
                "Environmental problems and solutions",
                "The importance of education"
            ],
            "speaking": [
                "Talk about your favorite hobby",
                "Describe a memorable trip",
                "Discuss technology's impact on society",
                "Explain a skill you would like to learn"
            ]
        }
    }

# --- ERROR HANDLERS ---
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist",
        "available_endpoints": [
            "/api/auth/login",
            "/api/auth/register", 
            "/api/essays/submit",
            "/api/ai/evaluate-essay",
            "/api/speaking/analyze-speaking",
            "/docs"
        ]
    }

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {
        "error": "Internal server error",
        "message": "Something went wrong on our end",
        "suggestion": "Please try again later or contact support"
    }

# --- SYSTEM INFO ---
@app.get("/api/system/info")
async def system_info():
    """Get system information"""
    return {
        "application": {
            "name": settings.app_name,
            "version": settings.version,
            "debug_mode": settings.debug
        },
        "features": {
            "ai_service": "Enhanced Free AI Service",
            "database": "SQLite (Development)",
            "authentication": "JWT with bcrypt",
            "file_upload": "Supported",
            "real_time_feedback": "Available"
        },
        "limits": {
            "max_file_size": f"{settings.max_file_size // (1024*1024)}MB",
            "supported_formats": ["audio/wav", "audio/mp3", "video/webm", "video/mp4"],
            "max_essay_length": "No limit",
            "max_speaking_time": "10 minutes"
        },
        "costs": {
            "essay_evaluation": "Free",
            "speaking_analysis": "Free", 
            "improvement_courses": "Free",
            "progress_tracking": "Free",
            "all_features": "100% Free"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)