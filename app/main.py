import os
import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from config.settings import settings
from app.database import init_db, get_db
from app.api.auth.auth import AuthService, UserCreate, UserLogin, Token, get_current_active_user
from app.api.routes.essays import router as essays_router
from app.api.routes.ai_grading import router as ai_router
from app.api.routes.speaking import router as speaking_router
from app.api.routes.admin import router as admin_router
from app.api.routes.dashboard import router as dashboard_router
from app.models.models import User

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Create uploads directory
os.makedirs(settings.upload_folder, exist_ok=True)

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application", app_name=settings.app_name, environment=settings.environment)
    
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise
    
    yield
    
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI-powered language learning backend with essay grading and speaking analysis",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None
)

# Security middleware
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["*"]  # Configure with your domain in production
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", 
                path=request.url.path, 
                method=request.method,
                error=str(exc),
                exc_info=True)
    
    if settings.debug:
        raise exc
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Health check endpoint (always available)
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        from app.database import async_engine
        async with async_engine.connect() as conn:
            await conn.execute("SELECT 1")
        
        db_status = "healthy"
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        db_status = "unhealthy"
    
    health_status = {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "environment": settings.environment,
        "version": settings.version
    }
    
    if settings.openai_api_key:
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
        "environment": settings.environment,
        "features": ["Authentication", "Essay Management", "AI Grading", "Speaking Analysis"],
        "ai_enabled": bool(settings.openai_api_key and settings.openai_api_key.startswith("sk-"))
    }

# Include routers
app.include_router(essays_router)
app.include_router(ai_router)
app.include_router(speaking_router)
app.include_router(admin_router)
app.include_router(dashboard_router)

# --- AUTHENTICATION ROUTES ---
@app.post("/api/auth/register", response_model=dict)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    try:
        existing_user = await AuthService.get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        new_user = await AuthService.create_user(db, user_data)
        
        logger.info("User registered successfully", user_id=new_user.id, email=new_user.email)
        
        return {
            "message": "User created successfully",
            "user_id": new_user.id,
            "email": new_user.email,
            "username": new_user.username
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("User registration failed", error=str(e))
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
        
        logger.info("User logged in successfully", user_id=user.id, email=user.email)
        
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login failed", email=login_data.email, error=str(e))
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

# Serve static files in production
if not settings.debug:
    app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        access_log=True
    )