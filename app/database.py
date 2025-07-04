from sqlachemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, create_async_engine
from sqlalchemy.orm import sessionmaker, Session
from config.settings import settings
from app.models.models import Base

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
)

async_engine = create_async_engine(
    settings.database_url_async,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionalLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
)

async def get_async_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def get_sync_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def create_tabkes():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class DatabaseManager:
    @staticmethod
    async def init_db():
        await create_tables()
        print("Tables created successfully")

    @staticmethod
    async def reset_db():
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        print("Datebase reset completed")