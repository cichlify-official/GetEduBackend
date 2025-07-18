from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from app.database import init_db, get_db
from app.api.auth.auth import AuthService, UserCreate, UserLogin, Token, get_current_active_user
from app.api.routes.essays import router as essays_router
from app.api.routes.ai_grading import router as ai_router
from app.models.models import User

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Starting {settings.app_name}")
    await init_db()
    yield
    print("👋 Shutting down gracefully")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI-powered language learning backend with essay grading and speaking analysis",
    lifespan=lifespan
)

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

# --- BASIC ROUTES ---
@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "status": "running",
        "features": ["Authentication", "Essay Management", "AI Grading", "Database"],
        "ai_enabled": bool(settings.openai_api_key and settings.openai_api_key.startswith("sk-"))
    }

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint that verifies database connectivity"""
    try:
        # Test database connection
        result = await db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
        "ai": "available",
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
        "username": new_user.username
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

# Import and include additional routers
try:
    from app.api.routes.speaking import router as speaking_router
    app.include_router(speaking_router)
except ImportError:
    print("⚠️ Speaking router not available")

try:
    from app.api.routes.admin import router as admin_router
    app.include_router(admin_router)
except ImportError:
    print("⚠️ Admin router not available")

try:
    from app.api.routes.dashboard import router as dashboard_router
    app.include_router(dashboard_router)
except ImportError:
    print("⚠️ Dashboard router not available")