# app/database.py - Final fix for Render deployment
import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import logging
from app.models.models import Base

logger = logging.getLogger(__name__)

def get_database_urls():
    """Get database URLs with fallback handling"""
    database_url = os.getenv("DATABASE_URL", "").strip()
    
    # If DATABASE_URL is empty or not set, use SQLite fallback
    if not database_url:
        logger.warning("No DATABASE_URL found, using SQLite fallback")
        database_url = "sqlite:///./app.db"
        database_url_async = "sqlite+aiosqlite:///./app.db"
        return database_url, database_url_async
    
    # Handle Render's postgres:// URLs
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # Create async version
    if "postgresql://" in database_url:
        database_url_async = database_url.replace("postgresql://", "postgresql+asyncpg://")
    elif "sqlite://" in database_url:
        database_url_async = database_url.replace("sqlite://", "sqlite+aiosqlite://")
    else:
        database_url_async = database_url
    
    logger.info(f"Using database: {database_url[:20]}...")
    return database_url, database_url_async

# Get database URLs
DATABASE_URL, DATABASE_URL_ASYNC = get_database_urls()

# Engine configuration
engine_kwargs = {
    "echo": False,  # Disable SQL logging in production
    "pool_pre_ping": True,
}

# Use NullPool for PostgreSQL (serverless friendly)
if "postgresql" in DATABASE_URL:
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs["pool_recycle"] = 3600

# Create async engine
try:
    async_engine = create_async_engine(DATABASE_URL_ASYNC, **engine_kwargs)
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

# Async session maker
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency for FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

# Initialize database with better error handling
async def init_db():
    """Initialize database tables with fallback"""
    try:
        # Test connection first
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        
        # Create all tables
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Don't raise the exception - let the app start and show the error in health check
        return False

# Database health check
async def check_db_health() -> dict:
    """Check database health and return status"""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "url_type": "postgresql" if "postgresql" in DATABASE_URL else "sqlite"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "url_type": "unknown"}