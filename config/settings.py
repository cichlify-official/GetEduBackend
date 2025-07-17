from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Language Learning AI Backend"
    debug: bool = False
    version: str = "1.0.0"
    
    # Server
    port: int = int(os.getenv("PORT", "8000"))
    host: str = "0.0.0.0"
    
    # Database - Use PostgreSQL from Render
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./language_ai.db")
    database_url_async: Optional[str] = None
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # AI APIs
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # File uploads
    upload_folder: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Post-process database URL after initialization
        if self.database_url_async is None:
            if self.database_url.startswith("postgres://"):
                # Render uses postgres:// but SQLAlchemy needs postgresql://
                self.database_url = self.database_url.replace("postgres://", "postgresql://", 1)
                self.database_url_async = self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif self.database_url.startswith("postgresql://"):
                self.database_url_async = self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            else:
                # Fallback to SQLite for local development
                self.database_url_async = "sqlite+aiosqlite:///./language_ai.db"

# Global settings instance
settings = Settings()