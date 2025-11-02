"""
Configuration management for the application
Loads environment variables and provides centralized config access
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv

# Load .env file explicitly before pydantic tries to use it
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application Settings
    APP_NAME: str = "AI Software Engineering Assistant"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True
    
    # API Keys - Model Providers
    GROQ_API_KEY: str
    CEREBRAS_API_KEY: str
    BYTEZ_API_KEY: str
    AZURE_AI_KEY: Optional[str] = None
    
    # API Keys - RAG Components
    VOYAGE_API_KEY: Optional[str] = None
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    
    # Cache/Database
    REDIS_URL: Optional[str] = None
    DATABASE_URL: str = "sqlite:///./data/app.db"
    

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_THRESHOLD: float = 0.8  # Switch at 80% of limit
    
    # Model Endpoints
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    CEREBRAS_BASE_URL: str = "https://api.cerebras.ai/v1"
    BYTEZ_BASE_URL: str = "https://api.bytez.com/v1"
    AZURE_AI_ENDPOINT: Optional[str] = None
    
    # Model Rate Limits (requests per minute)
    GROQ_RPM_LIMIT: int = 30
    GROQ_RPD_LIMIT: int = 14400
    CEREBRAS_TOKEN_LIMIT: int = 1000000
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    
    # Cache Settings
    CACHE_ENABLED: bool = True
    CACHE_TTL_DEFAULT: int = 3600
    CACHE_TTL_CODE_REVIEW: int = 7200
    CACHE_TTL_DOCUMENTATION: int = 86400
    CACHE_TTL_BUG_PREDICTION: int = 3600
    CACHE_TTL_CODE_GENERATION: int = 1800
    
    # Validation Settings
    VALIDATE_CODE_SECURITY: bool = True
    AUTO_DETECT_LANGUAGE: bool = True
    MAX_CODE_LENGTH: int = 50000
    MIN_CODE_LENGTH: int = 1
    
     # SECURITY FIX - Phase 1: Authentication Settings
    API_KEYS: Optional[str] = None  # Format: key1:user1:limit1,key2:user2:limit2
    AUTH_ENABLED: bool = True  # Set to False to disable auth (dev only!)
    
    # SECURITY FIX - Phase 1: Security Settings
    ENABLE_PROMPT_INJECTION_CHECK: bool = True
    ENABLE_SECRET_DETECTION: bool = True
    MAX_REQUEST_SIZE: int = 10485760  # 10MB
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export settings instance
settings = get_settings()