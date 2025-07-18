from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from config.settings import settings
from app.models.models import Base

# Async database engine
async_engine = create_async_engine(
    settings.database_url_async,
    echo=settings.debug
)

# Async session maker
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency for FastAPI
async def get_db():
    """Database dependency for FastAPI endpoints"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Initialize database
async def init_db():
    """Initialize database tables"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database initialized!")

# For compatibility with Celery workers (sync)
def get_sync_db():
    """Synchronous database session for Celery workers"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Convert async URL to sync URL for Celery
    sync_url = settings.database_url_async.replace("+aiosqlite", "")
    sync_engine = create_engine(sync_url)
    SessionLocal = sessionmaker(bind=sync_engine)
    return SessionLocal()