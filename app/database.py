import os
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import Base

# Get database URLs from environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./language_ai.db")
DATABASE_URL_ASYNC = os.getenv("DATABASE_URL_ASYNC", "sqlite+aiosqlite:///./language_ai.db")

# Debug: Print the database URLs
print(f"Database URL: {DATABASE_URL}")
print(f"Async Database URL: {DATABASE_URL_ASYNC}")

# Create engine configuration
engine_kwargs = {
    "echo": os.getenv("DEBUG", "false").lower() == "true",
}

# Handle SQLite specific configuration
if DATABASE_URL_ASYNC.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

try:
    # Create async database engine
    async_engine = create_async_engine(DATABASE_URL_ASYNC, **engine_kwargs)
    print("✅ Database engine created successfully")
except Exception as e:
    print(f"❌ Failed to create database engine: {e}")
    # Fallback to SQLite if the configured database fails
    DATABASE_URL_ASYNC = "sqlite+aiosqlite:///./language_ai.db"
    engine_kwargs = {
        "echo": False,
        "connect_args": {"check_same_thread": False}
    }
    async_engine = create_async_engine(DATABASE_URL_ASYNC, **engine_kwargs)
    print("✅ Fallback to SQLite database engine created")

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
        finally:
            await session.close()

# Initialize database
async def init_db():
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database initialized successfully!")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise e