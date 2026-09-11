import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env file."""
    PROJECT_NAME: str = "MATRIXCMS"
    PORTAL_TITLE: str = "MATRIXCMS: Expedition & Scientific Research Portal"
    INSTITUTION: str = "Chandigarh"
    DEPARTMENT: str = "CSE"
    
    # Database
    DATABASE_URL: str = "sqlite:///./matrixcms.db"
    
    # Security & Auth
    SECRET_KEY: str = "matrixcms_secret_key_change_in_production_f72389d7fae29bc"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Free LLM Settings (OpenAI-compatible)
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_API_KEY: str = "gsk_placeholder_replace_with_your_free_key"
    LLM_MODEL: str = "llama-3.1-8b-instruct"
    
    # Storage
    STORAGE_ROOT: str = "./storage/uploads"
    
    # Environment
    APP_ENV: str = "development"
    SCHEDULER_INTERVAL_MINUTES: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
