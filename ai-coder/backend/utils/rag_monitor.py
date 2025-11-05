"""
RAG Performance Monitoring
Tracks metrics for RAG operations
"""

import time
from typing import Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from utils.logger import logger

@dataclass
class RAGMetrics:
    """RAG operation metrics"""
    operation: str
    duration_ms: float
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)
    error: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class RAGMonitor:
    """Monitor RAG operations and performance"""
    
    def __init__(self):
        self.metrics: List[RAGMetrics] = []
        self.operation_counts = {}
        self.error_counts = {}
        self.max_metrics = 1000  # Keep last 1000 metrics
    
    def track_operation(
        self, 
        operation: str, 
        duration_ms: float, 
        success: bool, 
        error: str = None, 
        metadata: Dict[str, Any] = None
    ):
        """Track a RAG operation"""
        metric = RAGMetrics(
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            error=error,
            metadata=metadata or {}
        )
        
        self.metrics.append(metric)
        
        # Trim old metrics
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]
        
        # Update counts
        self.operation_counts[operation] = self.operation_counts.get(operation, 0) + 1
        
        if not success and error:
            self.error_counts[error] = self.error_counts.get(error, 0) + 1
        
        # Log operation
        if success:
            logger.info(f"RAG {operation} completed in {duration_ms:.2f}ms")
        else:
            logger.error(f"RAG {operation} failed in {duration_ms:.2f}ms: {error}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.metrics:
            return {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "success_rate": 0,
                "average_durations": {},
                "top_errors": [],
                "operation_counts": {}
            }
        
        # Calculate statistics
        total_operations = len(self.metrics)
        successful_operations = sum(1 for m in self.metrics if m.success)
        failed_operations = total_operations - successful_operations
        
        # Calculate average durations by operation
        avg_durations = {}
        for operation in set(m.operation for m in self.metrics):
            operation_metrics = [m for m in self.metrics if m.operation == operation]
            avg_durations[operation] = sum(m.duration_ms for m in operation_metrics) / len(operation_metrics)
        
        return {
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "failed_operations": failed_operations,
            "success_rate": successful_operations / total_operations if total_operations > 0 else 0,
            "average_durations": avg_durations,
            "top_errors": sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "operation_counts": self.operation_counts
        }
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics.clear()
        self.operation_counts.clear()
        self.error_counts.clear()

# Global monitor instance
rag_monitor = RAGMonitor()

def track_rag_operation(operation: str):
    """Decorator to track RAG operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                rag_monitor.track_operation(operation, duration_ms, True)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                rag_monitor.track_operation(operation, duration_ms, False, str(e))
                raise
        return wrapper
    return decorator