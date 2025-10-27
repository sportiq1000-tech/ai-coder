"""
Request schemas for API endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class PriorityLevel(str, Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class FeatureType(str, Enum):
    REVIEW = "review"
    DOCUMENT = "document"
    BUGS = "bugs"
    GENERATE = "generate"


class CodeLanguage(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    OTHER = "other"


class BaseRequest(BaseModel):
    """Base request model"""
    code: str = Field(..., min_length=1, max_length=50000)
    language: CodeLanguage = CodeLanguage.PYTHON
    context: Optional[str] = Field(None, max_length=10000)
    priority: PriorityLevel = PriorityLevel.NORMAL


class CodeReviewRequest(BaseRequest):
    """Request model for code review"""
    check_style: bool = True
    check_security: bool = True
    check_performance: bool = True


class DocumentationRequest(BaseRequest):
    """Request model for documentation generation"""
    include_examples: bool = True
    format: Literal["markdown", "docstring", "html"] = "markdown"


class BugPredictionRequest(BaseRequest):
    """Request model for bug prediction"""
    severity_threshold: Literal["low", "medium", "high"] = "medium"


class CodeGenerationRequest(BaseModel):
    """Request model for code generation"""
    description: str = Field(..., min_length=10, max_length=5000)
    language: CodeLanguage = CodeLanguage.PYTHON
    context: Optional[str] = Field(None, max_length=10000)
    include_tests: bool = False
    priority: PriorityLevel = PriorityLevel.NORMAL