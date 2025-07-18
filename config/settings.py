import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings optimized for Render deployment"""
    
    # Application
    app_name: str = "Language Learning AI Backend"
    debug: bool = False  # Set to False for production
    version: str = "1.0.0"
    
    # Database - Use environment variable or fallback to SQLite
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./language_ai.db")
    database_url_async: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./language_ai.db")
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # AI APIs
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Redis (for background tasks if available)
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # File uploads
    upload_folder: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    # Server settings for Render
    port: int = int(os.getenv("PORT", 8000))
    host: str = "0.0.0.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Convert PostgreSQL URL for async if needed
        if self.database_url.startswith("postgresql://"):
            self.database_url_async = self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        elif self.database_url.startswith("postgres://"):
            # Render uses postgres:// but SQLAlchemy needs postgresql://
            self.database_url = self.database_url.replace("postgres://", "postgresql://")
            self.database_url_async = self.database_url.replace("postgresql://", "postgresql+asyncpg://")

# Global settings instance
settings = Settings()