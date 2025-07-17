from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import os

from config.settings import settings
from app.database import init_db, get_db, check_db_health, close_db
from app.api.auth.auth import AuthService, UserCreate, UserLogin, Token, get_current_active_user
from app.api.routes.essays import router as essays_router
from app.api.routes.ai_grading import router as ai_router
from app.api.routes.speaking import router as speaking_router
from app.api.routes.admin import router as admin_router
from app.api.routes.dashboard import router as dashboard_router
from app.models.models import User

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
    description="AI-powered language learning backend with essay grading and speaking analysis",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else "/docs",  # Always enable docs for now
    redoc_url="/redoc" if settings.debug else None,
)

# CORS middleware - allow all for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(essays_router)
app.include_router(ai_router)
app.include_router(speaking_router)
app.include_router(admin_router)
app.include_router(dashboard_router)

# --- BASIC ROUTES ---
@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "status": "running",
        "environment": "production" if not settings.debug else "development",
        "features": ["Authentication", "Essay Management", "AI Grading", "Database"],
        "ai_enabled": bool(settings.openai_api_key and settings.openai_api_key.startswith("sk-"))
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
        "version": settings.version
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
            "username": new_user.username
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
            "token_type": "bearer"
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
        "created_at": current_user.created_at.isoformat()
    }

# --- DEMO ROUTES ---
@app.get("/api/demo/protected")
async def protected_demo(current_user: User = Depends(get_current_active_user)):
    return {
        "message": f"Hello {current_user.full_name}! This is a protected endpoint.",
        "user_id": current_user.id,
        "user_type": current_user.user_type
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)