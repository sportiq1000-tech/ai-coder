"""
Configuration management for the application
Loads environment variables and provides centralized config access
"""
from pydantic_settings import BaseSettings
from pydantic import Field
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
    
    # ============================================================================
    # RAG CONFIGURATION - Phase 1 (Original)
    # ============================================================================
    
    # RAG - Vector Store (Qdrant) - Additional Settings
    QDRANT_TIMEOUT: int = 30
    
    # RAG - Graph Store (Neo4j)
    NEO4J_URI: Optional[str] = None
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: Optional[str] = None
    NEO4J_DATABASE: str = "neo4j"
    NEO4J_MAX_CONNECTION_LIFETIME: int = 3600
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = 50
    
    # RAG - Chunking Configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MIN_CHUNK_SIZE: int = 50
    
    # RAG - Processing Configuration
    MAX_FILE_SIZE_MB: int = 10
    SUPPORTED_LANGUAGES: str = "python,javascript,typescript,java,cpp,csharp"
    EXCLUDE_PATTERNS: str = "*.pyc,__pycache__,node_modules,.git,*.min.js"
    
    # RAG - Performance Configuration
    PROCESSING_WORKERS: int = 4
    CACHE_EMBEDDINGS: bool = True
    CACHE_TTL: int = 3600
    
    # RAG - Quality Configuration
    MIN_RELEVANCE_SCORE: float = 0.7
    MAX_CHUNKS_PER_QUERY: int = 10
    
    # ============================================================================
    # RAG EMBEDDINGS CONFIGURATION - NEW (Phase 1 Update)
    # ============================================================================
    
    # Embedding Provider Selection
    EMBEDDING_PROVIDER: str = Field(default="smart", env="EMBEDDING_PROVIDER")
    
    # UPDATED: Embedding Defaults (Changed from 1536 to 768)
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")  # Kept for backward compatibility
    EMBEDDING_MODEL: str = Field(default="jina-embeddings-v2-base-en", env="EMBEDDING_MODEL")  # Changed default
    EMBEDDING_DIMENSION: int = Field(default=768, env="EMBEDDING_DIMENSION")  # Changed from 1536
    EMBEDDING_BATCH_SIZE: int = Field(default=100, env="EMBEDDING_BATCH_SIZE")
    
    # Jina AI Configuration (Primary)
    JINA_API_KEY: Optional[str] = Field(default=None, env="JINA_API_KEY") # NEW
    JINA_MODEL: str = Field(default="jina-embeddings-v2-base-en", env="JINA_MODEL")
    JINA_CACHE_DIR: str = Field(default="data/embeddings_cache/jina", env="JINA_CACHE_DIR")
    JINA_COMPRESSION: bool = Field(default=True, env="JINA_COMPRESSION")
    JINA_BATCH_SIZE: int = Field(default=100, env="JINA_BATCH_SIZE")
    JINA_TOKEN_LIMIT: int = Field(default=10_000_000, env="JINA_TOKEN_LIMIT")
    JINA_TOKEN_WARNING_THRESHOLD: float = Field(default=0.8, env="JINA_TOKEN_WARNING_THRESHOLD")
    
    # HuggingFace Configuration (Fallback 1 - Optional)
    HF_API_KEY: Optional[str] = Field(default=None, env="HF_API_KEY")
    HF_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", env="HF_MODEL")
    HF_CACHE_DIR: str = Field(default="data/embeddings_cache/huggingface", env="HF_CACHE_DIR")
    
    # Google Gemini Configuration (Fallback 2 - Optional)
    GEMINI_API_KEY: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    GEMINI_MODEL: str = Field(default="models/text-embedding-004", env="GEMINI_MODEL")
    GEMINI_CACHE_DIR: str = Field(default="data/embeddings_cache/gemini", env="GEMINI_CACHE_DIR")
    
    # Local Embeddings Configuration (Fallback 3 - Always Available)
    LOCAL_MODEL: str = Field(default="paraphrase-MiniLM-L3-v2", env="LOCAL_MODEL")
    LOCAL_CACHE_DIR: str = Field(default="data/embeddings_cache/local", env="LOCAL_CACHE_DIR")
    
    # Cache Configuration
    EMBEDDING_CACHE_ENABLED: bool = Field(default=True, env="EMBEDDING_CACHE_ENABLED")
    EMBEDDING_CACHE_COMPRESSION: bool = Field(default=True, env="EMBEDDING_CACHE_COMPRESSION")
    EMBEDDING_CACHE_TTL_DAYS: int = Field(default=30, env="EMBEDDING_CACHE_TTL_DAYS")
    EMBEDDING_CACHE_MAX_SIZE_GB: float = Field(default=1.0, env="EMBEDDING_CACHE_MAX_SIZE_GB")
    
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