from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import timedelta, datetime
import logging
import asyncio
import time
from sqlalchemy import select

from config.settings import settings
from app.database import init_db, get_db
from app.api.auth.auth import AuthService, UserCreate, UserLogin, Token, get_current_active_user
from app.models.models import User, UserRole
from app.utils.logging import setup_logging, MonitoringMiddleware

# Import all routers
from app.api.routes.essays import router as essays_router
from app.api.routes.ai_grading import router as ai_grading_router
from app.api.routes.speaking import router as speaking_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.admin import router as admin_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.scheduling import router as scheduling_router
from app.api.routes.curriculum import router as curriculum_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Lifespan events for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info(f"🚀 Starting {settings.app_name} v{settings.version}")
    
    try:
        # Initialize database
        await init_db()
        logger.info("✅ Database initialized successfully")
        
        # Initialize AI services
        from app.services.enhanced_ai_service import ai_service_manager
        logger.info("✅ AI services initialized")
        
        # Setup background tasks if Celery is available
        try:
            from workers.celery_app import celery_app
            logger.info("✅ Celery worker connection established")
        except ImportError:
            logger.warning("⚠️ Celery not available - background tasks disabled")
        
        logger.info("🎉 Application startup complete")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise
    
    yield
    
    logger.info("👋 Shutting down gracefully...")

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="""
    🎓 **AI-Powered Language Learning Backend**
    
    A comprehensive backend system for multi-language instruction with IELTS-style evaluation,
    personalized curriculum generation, and intelligent scheduling.
    
    ## Features
    
    ### 🧠 AI-Powered Assessment
    - **Essay Grading**: Automated IELTS-style scoring with detailed feedback
    - **Speaking Analysis**: Audio transcription and pronunciation assessment
    - **Fallback AI**: Open-source models when primary AI is unavailable
    
    ### 📚 Curriculum Management
    - **Personalized Learning**: AI-generated curriculums based on student performance
    - **Progress Tracking**: Real-time monitoring of learning progress
    - **Adaptive Content**: Dynamic difficulty adjustment based on performance
    
    ### 📅 Smart Scheduling
    - **Class Management**: Schedule, reschedule, and cancel classes
    - **Teacher Availability**: Flexible availability management
    - **Room Booking**: Virtual and physical classroom management
    
    ### 👨‍💼 Role-Based Access
    - **Students**: Submit assignments, track progress, schedule classes
    - **Teachers**: Manage classes, review student progress, set availability
    - **Admins**: Platform analytics, user management, system monitoring
    
    ### 🌍 Multi-Language Support
    - English, French, and Spanish instruction
    - Language-specific assessment criteria
    - Culturally appropriate content
    
    ## API Usage
    
    1. **Register/Login** to get access token
    2. **Submit content** for AI analysis
    3. **Track progress** through personalized dashboard
    4. **Schedule classes** with available teachers
    5. **Generate curriculum** based on learning goals
    
    ## Rate Limits & Costs
    
    - **Free Tier**: Rule-based analysis, unlimited usage
    - **AI Tier**: OpenAI-powered analysis, token-based pricing
    - **Automatic Fallback**: Seamless switching between AI services
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"] if settings.debug else ["yourdomain.com", "api.yourdomain.com"]
)

# CORS middleware - configure for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [
        "https://yourdomain.com",
        "https://app.yourdomain.com",
        "http://localhost:3000",  # Development frontend
        "http://localhost:5173"   # Vite development server
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time"]
)

# Monitoring middleware
app.add_middleware(MonitoringMiddleware)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later."
            }
        )

# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """Comprehensive health check"""
    start_time = time.time()
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.version,
        "environment": "development" if settings.debug else "production",
        "services": {}
    }
    
    # Check database
    try:
        from app.database import async_engine
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check AI services
    try:
        from app.services.enhanced_ai_service import ai_service_manager
        health_status["services"]["ai_primary"] = "available" if ai_service_manager.primary_service else "unavailable"
        health_status["services"]["ai_fallback"] = "available" if ai_service_manager.fallback_service else "unavailable"
    except Exception as e:
        health_status["services"]["ai_services"] = f"error: {str(e)}"
    
    # Check Celery (optional)
    try:
        from workers.celery_app import celery_app
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        health_status["services"]["celery"] = "healthy" if stats else "unhealthy"
    except Exception:
        health_status["services"]["celery"] = "unavailable"
    
    health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    return health_status

# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """API root endpoint with feature overview"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "status": "running",
        "features": {
            "authentication": "JWT-based with role management",
            "ai_grading": "Essay and speaking analysis",
            "scheduling": "Class and resource management", 
            "curriculum": "AI-generated personalized learning",
            "multi_language": "English, French, Spanish support",
            "admin_panel": "Analytics and user management"
        },
        "api_docs": "/docs",
        "admin_panel": "/docs#/Admin%20Dashboard",
        "health_check": "/health",
        "ai_enabled": bool(settings.openai_api_key and settings.openai_api_key.startswith("sk-")),
        "fallback_ai": "Available (rule-based analysis)"
    }

# Include all routers
app.include_router(essays_router)
app.include_router(ai_grading_router)
app.include_router(speaking_router)
app.include_router(dashboard_router)
app.include_router(admin_router)
app.include_router(tasks_router)
app.include_router(scheduling_router)
app.include_router(curriculum_router)

# --- AUTHENTICATION ROUTES ---

@app.post("/api/auth/register", response_model=dict, tags=["Authentication"])
async def register(user_data: UserCreate, db = Depends(get_db)):
    """
    Register a new user account
    
    Creates a new user with the specified role (student by default).
    Teachers and admins must be created by existing admins.
    """
    # Check if user already exists
    existing_user = await AuthService.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail="Email already registered. Please use a different email or try logging in."
        )
    
    # Check username availability
    username_check = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if username_check.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Username already taken. Please choose a different username."
        )
    
    try:
        new_user = await AuthService.create_user(db, user_data)
        
        # Create student profile if user is a student
        if new_user.role == UserRole.STUDENT:
            from app.models.models import StudentProfile
            student_profile = StudentProfile(user_id=new_user.id)
            db.add(student_profile)
            await db.commit()
        
        logger.info(f"New user registered: {new_user.email} ({new_user.role.value})")
        
        return {
            "message": "User created successfully",
            "user_id": new_user.id,
            "email": new_user.email,
            "username": new_user.username,
            "role": new_user.role.value,
            "next_steps": [
                "Log in with your credentials",
                "Complete your profile",
                "Start your learning journey!"
            ]
        }
        
    except Exception as e:
        logger.error(f"User registration failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Registration failed. Please try again."
        )

@app.post("/api/auth/login", response_model=Token, tags=["Authentication"])
async def login(login_data: UserLogin, db = Depends(get_db)):
    """
    User login with email and password
    
    Returns JWT access token for API authentication.
    Include token in Authorization header: `Bearer <token>`
    """
    user = await AuthService.authenticate_user(db, login_data.email, login_data.password)
    if not user:
        logger.warning(f"Failed login attempt for email: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password. Please check your credentials and try again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated. Please contact support.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = AuthService.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    logger.info(f"User logged in: {user.email} ({user.role.value})")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.value
        }
    }

@app.get("/api/auth/me", tags=["Authentication"])
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current authenticated user information
    
    Returns detailed user profile including role-specific data.
    """
    user_info = {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "preferred_language": current_user.preferred_language.value,
        "timezone": current_user.timezone,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }
    
    # Add role-specific information
    if current_user.role == UserRole.STUDENT:
        user_info.update({
            "ielts_target_band": current_user.ielts_target_band,
            "current_level": current_user.current_level
        })
    elif current_user.role == UserRole.TEACHER:
        user_info.update({
            "specializations": current_user.specializations or [],
            "hourly_rate": current_user.hourly_rate
        })
    
    return user_info

@app.post("/api/auth/refresh", tags=["Authentication"])
async def refresh_token(current_user: User = Depends(get_current_active_user)):
    """
    Refresh access token
    
    Generate a new access token for the current user.
    """
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = AuthService.create_access_token(
        data={"sub": current_user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60
    }

# --- DEMO & TESTING ROUTES ---

@app.get("/api/demo/protected", tags=["Demo"])
async def protected_demo(current_user: User = Depends(get_current_active_user)):
    """Demo endpoint showing authentication in action"""
    return {
        "message": f"Hello {current_user.full_name}! 🎉",
        "user_role": current_user.role.value,
        "access_level": "authenticated",
        "features_available": {
            "essay_submission": True,
            "speaking_analysis": True,
            "progress_tracking": True,
            "class_scheduling": current_user.role in [UserRole.STUDENT, UserRole.TEACHER],
            "admin_panel": current_user.role == UserRole.ADMIN,
            "curriculum_generation": current_user.role == UserRole.STUDENT
        }
    }

@app.get("/api/demo/public", tags=["Demo"])
async def public_demo():
    """Public demo endpoint (no authentication required)"""
    return {
        "message": "This is a public endpoint - no authentication required! 🌍",
        "available_features": [
            "User registration",
            "Health check",
            "API documentation",
            "Public information"
        ],
        "next_steps": [
            "Register an account at /api/auth/register",
            "Login at /api/auth/login",
            "Explore authenticated features"
        ],
        "sample_credentials": {
            "note": "Register your own account or use demo credentials",
            "demo_student": {
                "email": "student@demo.com",
                "password": "demopass123"
            }
        }
    }

# System information endpoint
@app.get("/api/system/info", tags=["System"])
async def system_info():
    """Get system information and capabilities"""
    
    ai_status = {
        "primary_ai": "available" if settings.openai_api_key else "not_configured",
        "fallback_ai": "available",
        "supported_languages": ["english", "french", "spanish"],
        "assessment_types": ["writing", "speaking", "reading", "listening"]
    }
    
    features = {
        "authentication": "JWT with role-based access",
        "ai_grading": "OpenAI GPT-4 + fallback models",
        "scheduling": "Smart class and resource management",
        "curriculum": "AI-generated personalized learning paths",
        "analytics": "Comprehensive progress tracking",
        "multi_language": "English, French, Spanish support",
        "background_tasks": "Async processing with Celery",
        "monitoring": "Request tracking and performance metrics"
    }
    
    return {
        "system_info": {
            "app_name": settings.app_name,
            "version": settings.version,
            "environment": "development" if settings.debug else "production",
            "database": "PostgreSQL" if "postgresql" in settings.database_url else "SQLite",
            "ai_services": ai_status,
            "features": features
        },
        "deployment_info": {
            "optimized_for": "Render.com deployment",
            "memory_efficient": True,
            "auto_scaling": True,
            "fallback_systems": True
        },
        "api_documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_spec": "/openapi.json"
        }
    }

# Performance monitoring endpoint
@app.get("/api/system/metrics", tags=["System"])
async def system_metrics(current_user: User = Depends(get_current_active_user)):
    """Get basic system metrics (admin only for detailed metrics)"""
    
    basic_metrics = {
        "server_time": datetime.utcnow().isoformat(),
        "uptime_check": "healthy",
        "api_version": settings.version
    }
    
    # Detailed metrics for admins
    if current_user.role == UserRole.ADMIN:
        try:
            from app.database import async_engine
            
            # Database connection pool status
            pool_status = {
                "pool_size": async_engine.pool.size() if hasattr(async_engine.pool, 'size') else "unknown",
                "checked_out": async_engine.pool.checkedout() if hasattr(async_engine.pool, 'checkedout') else "unknown"
            }
            
            basic_metrics.update({
                "database_pool": pool_status,
                "memory_usage": "Available in production monitoring",
                "active_connections": "Available in production monitoring"
            })
            
        except Exception as e:
            basic_metrics["monitoring_error"] = str(e)
    
    return basic_metrics

if __name__ == "__main__":
    import uvicorn
    
    # Development server configuration
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        workers=1 if settings.debug else 4,
        log_level="info" if settings.debug else "warning",
        access_log=settings.debug
    )