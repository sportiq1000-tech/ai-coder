"""
RAG-related Pydantic schemas
Defines data models for RAG components
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class CodeChunk(BaseModel):
    """Represents a chunk of code"""
    id: Optional[str] = None
    content: str
    file_path: str
    language: str
    chunk_type: str  # function, class, method, generic
    start_line: int
    end_line: int
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "main.py:10-25",
                "content": "def hello():\n    return 'Hello, World!'",
                "file_path": "main.py",
                "language": "python",
                "chunk_type": "function",
                "start_line": 10,
                "end_line": 25,
                "metadata": {"name": "hello", "complexity": 1}
            }
        }

class CodeNode(BaseModel):
    """Represents a node in the code graph"""
    id: str
    type: str  # file, function, class, module
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "main.py",
                "type": "file",
                "properties": {"language": "python", "lines_of_code": 100}
            }
        }

class CodeRelationship(BaseModel):
    """Represents a relationship between code nodes"""
    source_id: str
    target_id: str
    type: str  # CONTAINS, CALLS, IMPORTS, EXTENDS
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "source_id": "main.py",
                "target_id": "utils.py",
                "type": "IMPORTS",
                "properties": {"line_number": 1}
            }
        }

class SearchResult(BaseModel):
    """Represents a search result from vector store"""
    id: str
    content: str
    file_path: str
    language: str
    chunk_type: str
    start_line: int
    end_line: int
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "main.py:10-25",
                "content": "def hello():\n    return 'Hello, World!'",
                "file_path": "main.py",
                "language": "python",
                "chunk_type": "function",
                "start_line": 10,
                "end_line": 25,
                "score": 0.95,
                "metadata": {"name": "hello"}
            }
        }

class GraphQueryResult(BaseModel):
    """Represents a result from graph query"""
    id: str
    type: str
    properties: Dict[str, Any]
    path: Optional[List[str]] = None
    depth: Optional[int] = None
    similarity: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "utils.py:calculate",
                "type": "function",
                "properties": {"name": "calculate", "complexity": 3},
                "path": ["main.py", "utils.py", "calculate"],
                "depth": 2
            }
        }

class ProcessingStatus(BaseModel):
    """Represents the status of a processing job"""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: float = Field(ge=0, le=1)
    message: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_123",
                "status": "processing",
                "progress": 0.5,
                "message": "Processing file 5 of 10",
                "started_at": "2025-01-05T10:00:00Z"
            }
        }