import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import structlog
from config.settings import settings
from app.models.models import Base

logger = structlog.get_logger()

# Production database configuration
engine_kwargs = {
    "echo": settings.debug,
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}

# Use NullPool for serverless environments like Render
if settings.is_production:
    engine_kwargs["poolclass"] = NullPool

# Async database engine
async_engine = create_async_engine(
    settings.database_url_async,
    **engine_kwargs
)

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
            logger.error("Database session error", error=str(e))
            raise
        finally:
            await session.close()

# Initialize database
async def init_db():
    """Initialize database tables"""
    try:
        async with async_engine.begin() as conn:
            # Test connection first
            await conn.execute(text("SELECT 1"))
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise

# Database health check
async def check_db_health() -> bool:
    """Check if database is accessible"""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False

# Database manager for migrations and utilities
class DatabaseManager:
    @staticmethod
    async def reset_db():
        """Reset database (DANGER: deletes all data)"""
        if not settings.debug:
            raise Exception("Database reset only allowed in debug mode")
        
        logger.warning("Resetting database - all data will be lost")
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database reset complete")
    
    @staticmethod
    async def get_table_info():
        """Get database table information"""
        async with async_engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """))
            return result.fetchall()