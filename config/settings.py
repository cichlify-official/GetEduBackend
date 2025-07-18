from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    """Production-ready application settings with Celery support"""
    
    # Application
    app_name: str = "Language Learning AI Backend"
    debug: bool = False
    version: str = "2.0.0"
    environment: str = "production"
    
    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/language_ai")
    database_url_async: str = os.getenv("DATABASE_URL_ASYNC", "postgresql+asyncpg://user:password@localhost:5432/language_ai")
    
    # Redis Configuration (for Celery and caching)
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Security Configuration
    secret_key: str = os.getenv("SECRET_KEY", "change-this-in-production-use-long-random-string")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60  # 1 hour
    
    # AI Service Configuration
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_timeout: int = 30
    openai_max_retries: int = 3
    
    # Fallback AI Configuration
    enable_fallback_ai: bool = True
    fallback_model_path: str = "./models"  # Local model storage
    
    # File Upload Configuration
    upload_folder: str = "uploads"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_audio_formats: List[str] = ["mp3", "wav", "m4a", "webm"]
    allowed_document_formats: List[str] = ["txt", "pdf", "docx"]
    
    # Rate Limiting
    rate_limit_per_minute: int = 100
    ai_rate_limit_per_hour: int = 50
    
    # CORS Configuration
    allowed_origins: List[str] = [
        "https://yourdomain.com",
        "https://app.yourdomain.com",
        "https://admin.yourdomain.com"
    ]
    
    # Monitoring & Logging
    log_level: str = "INFO"
    enable_sentry: bool = False
    sentry_dsn: Optional[str] = os.getenv("SENTRY_DSN")
    
    # Email Configuration (for notifications)
    smtp_server: Optional[str] = os.getenv("SMTP_SERVER")
    smtp_port: int = 587
    smtp_username: Optional[str] = os.getenv("SMTP_USERNAME")
    smtp_password: Optional[str] = os.getenv("SMTP_PASSWORD")
    from_email: str = os.getenv("FROM_EMAIL", "noreply@yourdomain.com")
    
    # Celery Configuration
    celery_broker_url: str = redis_url
    celery_result_backend: str = redis_url
    celery_task_serializer: str = "json"
    celery_accept_content: List[str] = ["json"]
    celery_result_serializer: str = "json"
    celery_timezone: str = "UTC"
    celery_enable_utc: bool = True
    
    # Celery Worker Configuration
    celery_worker_concurrency: int = 2  # Number of worker processes
    celery_worker_prefetch_multiplier: int = 1
    celery_task_acks_late: bool = True
    celery_worker_max_tasks_per_child: int = 50
    celery_worker_max_memory_per_child: int = 200000  # 200MB
    
    # Celery Task Configuration
    celery_task_soft_time_limit: int = 300  # 5 minutes
    celery_task_time_limit: int = 600       # 10 minutes
    celery_task_reject_on_worker_lost: bool = True
    celery_task_ignore_result: bool = False
    
    # Performance Settings
    database_pool_size: int = 20
    database_max_overflow: int = 0
    request_timeout: int = 30
    
    # Feature Flags
    enable_curriculum_generation: bool = True
    enable_speaking_analysis: bool = True
    enable_class_scheduling: bool = True
    enable_admin_analytics: bool = True
    enable_background_tasks: bool = True
    
    # Development overrides
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Development mode adjustments
        if self.debug:
            self.database_url = "sqlite:///./language_ai.db"
            self.database_url_async = "sqlite+aiosqlite:///./language_ai.db"
            self.redis_url = "redis://localhost:6379/0"
            self.allowed_origins = ["*"]
            self.celery_worker_concurrency = 1  # Single worker for development
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
