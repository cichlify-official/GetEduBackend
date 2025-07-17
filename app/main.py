# app/main.py - Minimal version that will start on Render
import os
import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import secrets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Simple settings without Pydantic complexity
class SimpleSettings:
    def __init__(self):
        self.app_name = "Language Learning AI Backend"
        self.version = "1.0.0"
        self.debug = False
        self.environment = "production"
        self.host = "0.0.0.0"
        self.port = int(os.getenv("PORT", "8000"))
        self.secret_key = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
        self.access_token_expire_minutes = 1440
        self.upload_folder = "/tmp/uploads"
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

settings = SimpleSettings()
logger.info(f"Settings loaded: {settings.app_name}")

# Import database and models after settings
try:
    from app.database import init_db, get_db, check_db_health
    from app.models.models import User
    logger.info("Database imports successful")
except Exception as e:
    logger.error(f"Database import failed: {e}")
    # Create dummy functions so app can start
    async def init_db(): return False
    async def get_db(): yield None
    async def check_db_health(): return {"status": "unavailable", "error": str(e)}

# Import auth after settings
try:
    from app.api.auth.auth import AuthService, UserCreate, UserLogin, Token, get_current_active_user
    logger.info("Auth imports successful")
except Exception as e:
    logger.error(f"Auth import failed: {e}")

# Create uploads directory
os.makedirs(settings.upload_folder, exist_ok=True)

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name}")
    
    # Try to initialize database, but don't fail if it doesn't work
    try:
        db_success = await init_db()
        if db_success:
            logger.info("Database initialized successfully")
        else:
            logger.warning("Database initialization failed - app will start anyway")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
    
    yield
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI-powered language learning backend",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "path": str(request.url.path)}
    )

# Health check endpoint (most important for Render)
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "port": settings.port
    }
    
    # Check database
    try:
        db_health = await check_db_health()
        health_status["database"] = db_health
    except Exception as e:
        health_status["database"] = {"status": "error", "error": str(e)}
    
    # Check AI
    if settings.openai_api_key and settings.openai_api_key.startswith("sk-"):
        health_status["ai"] = "configured"
    else:
        health_status["ai"] = "not_configured"
    
    return health_status

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "environment": settings.environment
    }

# Basic test endpoint
@app.get("/test")
async def test_endpoint():
    """Simple test endpoint to verify app is working"""
    return {
        "message": "App is working!",
        "timestamp": "2025-07-17",
        "environment": settings.environment
    }

# Authentication endpoints (with error handling)
@app.post("/api/auth/register")
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")
            
        existing_user = await AuthService.get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        new_user = await AuthService.create_user(db, user_data)
        logger.info(f"User registered: {new_user.email}")
        
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

@app.post("/api/auth/login")
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login user and return JWT token"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")
            
        user = await AuthService.authenticate_user(db, login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
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
                "username": user.username
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

# Include other routers with error handling
routers_to_include = [
    ("app.api.routes.essays", "essays_router", "Essays"),
    ("app.api.routes.ai_grading", "ai_router", "AI Grading"),
    ("app.api.routes.speaking", "speaking_router", "Speaking"),
    ("app.api.routes.admin", "admin_router", "Admin"),
    ("app.api.routes.dashboard", "dashboard_router", "Dashboard")
]

for module_name, router_name, description in routers_to_include:
    try:
        module = __import__(module_name, fromlist=[router_name])
        router = getattr(module, router_name)
        app.include_router(router)
        logger.info(f"{description} router included")
    except Exception as e:
        logger.warning(f"Failed to include {description} router: {e}")

logger.info(f"🚀 {settings.app_name} is ready to start!")