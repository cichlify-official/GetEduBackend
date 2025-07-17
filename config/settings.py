import os
from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    """Application settings optimized for production"""
    
    # Application
    app_name: str = "Language Learning AI Backend"
    version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database - Production PostgreSQL
    database_url: str = ""
    database_url_async: str = ""
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    
    # CORS
    allowed_origins: List[str] = ["*"]
    allowed_methods: List[str] = ["*"]
    allowed_headers: List[str] = ["*"]
    
    # AI APIs
    openai_api_key: Optional[str] = None
    
    # Redis (for background tasks)
    redis_url: str = "redis://localhost:6379/0"
    
    # File uploads
    upload_folder: str = "/tmp/uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    # Logging
    log_level: str = "INFO"
    
    # Health check
    health_check_path: str = "/health"
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    @property
    def database_url_sync(self) -> str:
        """Convert async URL to sync for Alembic"""
        return self.database_url.replace("+asyncpg", "").replace("+aiosqlite", "")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Auto-configure database URLs if not set
        if not self.database_url and os.getenv("DATABASE_URL"):
            db_url = os.getenv("DATABASE_URL")
            # Handle Render's postgres:// URLs
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            
            self.database_url = db_url
            self.database_url_async = db_url.replace("postgresql://", "postgresql+asyncpg://")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()