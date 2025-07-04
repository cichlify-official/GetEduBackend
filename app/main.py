from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config.settings import settings
from app.database import init_db, get_db
from sqlalchemy.ext.asyncio import AsyncSession

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🚀 Starting {settings.app_name}")
    await init_db()
    yield
    # Shutdown
    print("👋 Shutting down gracefully")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI-powered language learning backend",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}

@app.get("/api/demo/hello")
async def hello_world():
    return {"message": "Hello from your language learning backend!"}

@app.post("/api/demo/echo")
async def echo(data: dict):
    return {"echo": data, "received": True}

# Demo database endpoint
@app.get("/api/demo/db-test")
async def test_database(db: AsyncSession = Depends(get_db)):
    return {"message": "Database connection successful!", "db_type": "SQLite"}
