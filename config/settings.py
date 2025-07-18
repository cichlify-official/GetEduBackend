import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings with proper defaults for deployment"""
    
    # Application
    app_name: str = "GetEdu - AI Language Learning"
    debug: bool = False
    version: str = "1.0.0"
    
    # Database - Use SQLite by default for simplicity
    database_url: str = "sqlite:///./language_ai.db"
    database_url_async: str = "sqlite+aiosqlite:///./language_ai.db"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # AI APIs (optional)
    openai_api_key: Optional[str] = None
    
    # File uploads
    upload_folder: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    # Redis (optional)
    redis_url: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Override with environment variables if they exist
        self.database_url = os.getenv("DATABASE_URL", self.database_url)
        self.database_url_async = os.getenv("DATABASE_URL_ASYNC", self.database_url_async)
        self.secret_key = os.getenv("SECRET_KEY", self.secret_key)
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.openai_api_key = os.getenv("OPENAI_API_KEY", self.openai_api_key)
        
        # Ensure SQLite is used if no database URL is provided
        if not self.database_url or self.database_url == "":
            self.database_url = "sqlite:///./language_ai.db"
            self.database_url_async = "sqlite+aiosqlite:///./language_ai.db"
        
        # If database_url is set but database_url_async is not, derive it
        if self.database_url and not self.database_url_async:
            if self.database_url.startswith("sqlite"):
                self.database_url_async = self.database_url.replace("sqlite://", "sqlite+aiosqlite://")
            elif self.database_url.startswith("postgresql"):
                self.database_url_async = self.database_url.replace("postgresql://", "postgresql+asyncpg://")

# Global settings instance
settings = Settings()

# Debug print
print(f"🔧 Settings loaded:")
print(f"   App Name: {settings.app_name}")
print(f"   Debug Mode: {settings.debug}")
print(f"   Database URL: {settings.database_url}")
print(f"   Async Database URL: {settings.database_url_async}")
print(f"   OpenAI API Key: {'Set' if settings.openai_api_key else 'Not set'}")
print(f"   Secret Key: {'Set' if settings.secret_key != 'your-secret-key-change-in-production' else 'Default (change in production)'}")