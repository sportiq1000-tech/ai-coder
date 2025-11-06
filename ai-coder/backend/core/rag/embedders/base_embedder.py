"""
Base Embedder Abstract Class
Defines the interface all embedders must implement
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EmbedderStats:
    """Statistics for an embedder"""
    total_requests: int = 0
    total_texts: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_errors: int = 0
    last_error: Optional[str] = None
    last_request_time: Optional[datetime] = None
    average_latency_ms: float = 0.0


class BaseEmbedder(ABC):
    """
    Abstract base class for all embedding implementations
    
    All embedders must implement:
    - embed_batch(): Embed multiple texts
    - health_check(): Verify embedder is operational
    """
    
    def __init__(self, 
                 model_name: str,
                 dimension: int,
                 batch_size: int = 100,
                 requires_api_key: bool = False):
        """
        Initialize base embedder
        
        Args:
            model_name: Name of the embedding model
            dimension: Output dimension of embeddings
            batch_size: Maximum texts per batch
            requires_api_key: Whether API key is required
        """
        self.model_name = model_name
        self.dimension = dimension
        self.batch_size = batch_size
        self.requires_api_key = requires_api_key
        self.stats = EmbedderStats()
        
    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Embed a batch of texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings (None for failed embeddings)
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if embedder is healthy and operational
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    async def embed_single(self, text: str) -> Optional[List[float]]:
        """
        Embed a single text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if failed
        """
        results = await self.embed_batch([text])
        return results[0] if results else None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get embedder statistics
        
        Returns:
            Statistics dictionary
        """
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "batch_size": self.batch_size,
            "requires_api_key": self.requires_api_key,
            "total_requests": self.stats.total_requests,
            "total_texts": self.stats.total_texts,
            "cache_hits": self.stats.cache_hits,
            "cache_misses": self.stats.cache_misses,
            "total_errors": self.stats.total_errors,
            "cache_hit_rate": self.stats.cache_hits / max(1, self.stats.total_requests),
            "average_latency_ms": self.stats.average_latency_ms
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = EmbedderStats()
    
    def _pad_or_truncate(self, embedding: List[float], target_dim: int) -> List[float]:
        """
        Pad or truncate embedding to target dimension
        
        Args:
            embedding: Input embedding
            target_dim: Target dimension
            
        Returns:
            Adjusted embedding
        """
        current_dim = len(embedding)
        
        if current_dim == target_dim:
            return embedding
        elif current_dim < target_dim:
            # Pad with zeros
            return embedding + [0.0] * (target_dim - current_dim)
        else:
            # Truncate
            return embedding[:target_dim]
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model_name}, dim={self.dimension})"