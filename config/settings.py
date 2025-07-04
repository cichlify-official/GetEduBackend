from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Language Learning AI Backend"
    debug: bool = True
    version: str = "1.0.0"
    
    # Database (SQLite for development)
    database_url: str = "sqlite:///./language_ai.db"
    database_url_async: str = "sqlite+aiosqlite:///./language_ai.db"
    
    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # AI APIs
    openai_api_key: Optional[str] = None
    
    # File uploads
    upload_folder: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    class Config:
        env_file = ".env"

# Global settings instance
settings = Settings()
