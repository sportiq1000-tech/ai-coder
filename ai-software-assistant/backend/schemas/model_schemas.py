"""
Model-specific schemas and configurations
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum


class ModelProvider(str, Enum):
    GROQ = "groq"
    CEREBRAS = "cerebras"
    BYTEZ = "bytez"
    AZURE = "azure"


class ModelName(str, Enum):
    # Groq Models
    LLAMA_70B = "llama-3.1-70b-versatile"
    LLAMA_8B = "llama-3.1-8b-instant"
    MIXTRAL_8X7B = "mixtral-8x7b-32768"
    GEMMA_9B = "gemma2-9b-it"
    
    # Cerebras Models
    CEREBRAS_LLAMA_70B = "llama3.1-70b"
    CEREBRAS_LLAMA_8B = "llama3.1-8b"
    
    # Azure Models
    PHI_3_MINI = "Phi-3-mini-4k-instruct"
    PHI_3_MEDIUM = "Phi-3-medium-4k-instruct"


class ModelConfig(BaseModel):
    """Configuration for a model"""
    provider: ModelProvider
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    context_window: int = 8192
    rpm_limit: Optional[int] = None
    rpd_limit: Optional[int] = None


class ModelRequest(BaseModel):
    """Request to a model"""
    model: str
    messages: list
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.9
    stream: bool = False


class ModelResponse(BaseModel):
    """Response from a model"""
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None