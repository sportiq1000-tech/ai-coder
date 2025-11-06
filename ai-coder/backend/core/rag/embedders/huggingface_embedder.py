"""
HuggingFace Embedder
First fallback with 30K requests/month free
"""

import requests
import time
from typing import List, Optional
from datetime import datetime
from utils.logger import logger
from utils.config import get_settings
from .base_embedder import BaseEmbedder
from .cache_manager import CacheManager


class HuggingFaceEmbedder(BaseEmbedder):
    """
    HuggingFace Inference API embedder
    
    Features:
    - 30,000 requests/month free (with API key)
    - Various models available
    - 384 dimensions (padded to 768)
    """
    
    API_URL_TEMPLATE = "https://api-inference.huggingface.co/pipeline/feature-extraction/{model}"
    
    def __init__(self):
        """Initialize HuggingFace embedder"""
        settings = get_settings()
        
        model = getattr(settings, 'HF_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        api_key = getattr(settings, 'HF_API_KEY', None)
        dimension = 768  # Padded from 384
        batch_size = 32  # HF has lower batch limits
        
        super().__init__(
            model_name=model,
            dimension=dimension,
            batch_size=batch_size,
            requires_api_key=True
        )
        
        self.api_key = api_key
        self.api_url = self.API_URL_TEMPLATE.format(model=model)
        self.native_dimension = 384  # Most sentence-transformers models
        
        # Cache
        cache_dir = getattr(settings, 'HF_CACHE_DIR', 'data/embeddings_cache/huggingface')
        self.cache = CacheManager(cache_dir=cache_dir, compression=True)
        
        # HTTP session
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })
        
        logger.info(f"HuggingFaceEmbedder initialized: {model}")
    
    async def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Embed texts using HuggingFace API
        
        Args:
            texts: List of texts
            
        Returns:
            List of embeddings (padded to 768-dim)
        """
        if not texts:
            return []
        
        if not self.api_key:
            logger.warning("HuggingFace API key not configured")
            return [None] * len(texts)
        
        start_time = time.time()
        self.stats.total_requests += 1
        self.stats.total_texts += len(texts)
        
        # Check cache
        cached_embeddings = self.cache.get_batch(texts, self.model_name)
        uncached_indices = [i for i, emb in enumerate(cached_embeddings) if emb is None]
        uncached_texts = [texts[i] for i in uncached_indices]
        
        self.stats.cache_hits += len(texts) - len(uncached_texts)
        self.stats.cache_misses += len(uncached_texts)
        
        if not uncached_texts:
            return cached_embeddings
        
        # Process in batches (HF Inference API has smaller limits)
        new_embeddings = []
        for i in range(0, len(uncached_texts), self.batch_size):
            batch = uncached_texts[i:i + self.batch_size]
            
            try:
                response = self.session.post(
                    self.api_url,
                    json={"inputs": batch},
                    timeout=30
                )
                
                response.raise_for_status()
                batch_embeddings = response.json()
                
                # Pad embeddings to 768 dimensions
                padded = [
                    self._pad_or_truncate(emb, self.dimension)
                    for emb in batch_embeddings
                ]
                new_embeddings.extend(padded)
                
            except Exception as e:
                logger.error(f"HuggingFace API error for batch: {e}")
                new_embeddings.extend([None] * len(batch))
                self.stats.total_errors += 1
        
        # Cache new embeddings
        self.cache.set_batch(uncached_texts, self.model_name, new_embeddings)
        
        # Merge results
        result = []
        new_idx = 0
        for cached_emb in cached_embeddings:
            if cached_emb is not None:
                result.append(cached_emb)
            else:
                result.append(new_embeddings[new_idx])
                new_idx += 1
        
        # Update stats
        elapsed_ms = (time.time() - start_time) * 1000
        self.stats.average_latency_ms = (
            (self.stats.average_latency_ms * (self.stats.total_requests - 1) + elapsed_ms) 
            / self.stats.total_requests
        )
        self.stats.last_request_time = datetime.now()
        
        return result
    
    def health_check(self) -> bool:
        """Check if HuggingFace API is accessible"""
        if not self.api_key:
            return False
        
        try:
            response = self.session.post(
                self.api_url,
                json={"inputs": ["test"]},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"HuggingFace health check failed: {e}")
            return False