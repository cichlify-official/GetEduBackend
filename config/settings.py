# config/settings.py - Render deployment fix
import os
from pydantic_settings import BaseSettings
from typing import Optional, List
import secrets

class Settings(BaseSettings):
    """Application settings optimized for Render deployment"""
    
    # Application
    app_name: str = "Language Learning AI Backend"
    version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"
    
    # Server - Render automatically sets PORT
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", "8000"))
    
    # Database - Will be auto-filled by Render
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    database_url_async: str = ""
    
    # Security - Generate if not provided
    secret_key: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    
    # CORS
    allowed_origins: List[str] = ["*"]  # Configure properly in production
    allowed_methods: List[str] = ["*"]
    allowed_headers: List[str] = ["*"]
    
    # AI APIs
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Redis - Will be auto-filled by Render
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # File uploads - Use /tmp for serverless
    upload_folder: str = "/tmp/uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    # Logging
    log_level: str = "INFO"
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    @property
    def database_url_sync(self) -> str:
        """Convert async URL to sync for Alembic"""
        return self.database_url.replace("+asyncpg", "").replace("+aiosqlite", "")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Handle Render database URL conversion
        if self.database_url and self.database_url.startswith("postgres://"):
            # Convert postgres:// to postgresql:// for SQLAlchemy
            self.database_url = self.database_url.replace("postgres://", "postgresql://", 1)
        
        # Set async URL if not already set
        if not self.database_url_async:
            if "postgresql://" in self.database_url:
                self.database_url_async = self.database_url.replace("postgresql://", "postgresql+asyncpg://")
            elif "sqlite://" in self.database_url:
                self.database_url_async = self.database_url.replace("sqlite://", "sqlite+aiosqlite://")
            else:
                self.database_url_async = self.database_url
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()