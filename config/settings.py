from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    app_name: str = "GetEduBackend"
    debug: bool = False
    version: str = "MVP"
    database_url: str = ""
    database_url_async: str = ""
    redis_url: str = "redis://localhost:6379"
    secret_key: str = "secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    whisper_api_key: Optional[str] = os.getenv("WHISPER_API_KEY")
    max_file_size: int = 10 * 1024 * 1024
    upload_folder: str = "uploads"
    rate_limit_per_minute: int = 80
    ai_requests_per_day: int = 100

    class Config:
        env_file = ".env"

settings = Settings()