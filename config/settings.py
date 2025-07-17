from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "GET Education Platform"
    debug: bool = False
    version: str = "1.0.0"
    
    # Database - use persistent volume in production
    database_url: str = "sqlite:///./data/get_education.db"
    database_url_async: str = "sqlite+aiosqlite:///./data/get_education.db"
    
    # Security
    secret_key: str = "production-secret-key-change-this"
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
