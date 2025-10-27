"""
Metrics and usage tracking
"""
from typing import Dict, Any
from datetime import datetime
import json
from pathlib import Path
from utils.logger import logger


class MetricsCollector:
    """Collect and store usage metrics"""
    
    def __init__(self):
        self.metrics_file = Path("data/metrics.jsonl")
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log_request(
        self,
        endpoint: str,
        task_type: str,
        model_used: str,
        provider: str,
        tokens_used: int,
        processing_time_ms: float,
        status: str,
        error: str = None
    ):
        """Log a request to metrics file"""
        metric = {
            'timestamp': datetime.utcnow().isoformat(),
            'endpoint': endpoint,
            'task_type': task_type,
            'model': model_used,
            'provider': provider,
            'tokens': tokens_used,
            'processing_time_ms': processing_time_ms,
            'status': status,
            'error': error
        }
        
        try:
            with open(self.metrics_file, 'a') as f:
                f.write(json.dumps(metric) + '\n')
        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")
    
    def get_stats(self, last_n: int = 100) -> Dict[str, Any]:
        """Get usage statistics"""
        if not self.metrics_file.exists():
            return {'total_requests': 0}
        
        metrics = []
        try:
            with open(self.metrics_file, 'r') as f:
                lines = f.readlines()
                for line in lines[-last_n:]:
                    metrics.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to read metrics: {e}")
            return {'error': str(e)}
        
        if not metrics:
            return {'total_requests': 0}
        
        # Calculate stats
        total_requests = len(metrics)
        total_tokens = sum(m.get('tokens', 0) for m in metrics)
        avg_time = sum(m.get('processing_time_ms', 0) for m in metrics) / total_requests
        
        # Count by provider
        providers = {}
        for m in metrics:
            provider = m.get('provider', 'unknown')
            providers[provider] = providers.get(provider, 0) + 1
        
        # Count by task
        tasks = {}
        for m in metrics:
            task = m.get('task_type', 'unknown')
            tasks[task] = tasks.get(task, 0) + 1
        
        return {
            'total_requests': total_requests,
            'total_tokens': total_tokens,
            'avg_processing_time_ms': round(avg_time, 2),
            'providers': providers,
            'tasks': tasks,
            'period': f'Last {total_requests} requests'
        }


# Global instance
_metrics_instance = None

def get_metrics() -> MetricsCollector:
    """Get singleton metrics collector"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsCollector()
    return _metrics_instance