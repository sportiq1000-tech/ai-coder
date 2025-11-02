"""
Response schemas for API endpoints
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    QUEUED = "queued"
    PROCESSING = "processing"


class BaseResponse(BaseModel):
    """Base response model"""
    status: ResponseStatus
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ModelInfo(BaseModel):
    """Model information in response"""
    model_name: str
    provider: str
    tokens_used: Optional[int] = None
    processing_time_ms: Optional[float] = None
    model_config = ConfigDict(
        protected_namespaces=()  # ← ADD THIS LINE
    )

class APIResponse(BaseResponse):
    """Standard API response"""
    data: Optional[Any] = None
    model_info: Optional[ModelInfo] = None
    request_id: Optional[str] = None
    model_config = ConfigDict(protected_namespaces=())  # ← FIX


class ErrorResponse(BaseResponse):
    """Error response model"""
    status: ResponseStatus = ResponseStatus.ERROR
    error_code: str
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    uptime_seconds: float
    models_available: Dict[str, bool]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(protected_namespaces=())  # ← ADD IF NEEDED