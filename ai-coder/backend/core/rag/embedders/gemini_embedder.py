"""
Google Gemini Embedder
Second fallback with generous rate limits
"""

import time
from typing import List, Optional
from datetime import datetime
from utils.logger import logger
from utils.config import get_settings
from .base_embedder import BaseEmbedder
from .cache_manager import CacheManager

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-generativeai not installed, Gemini embedder unavailable")


class GeminiEmbedder(BaseEmbedder):
    """
    Google Gemini embedding implementation
    
    Features:
    - Unlimited (with rate limits: 15 req/min)
    - 768 dimensions
    - Free tier available
    """
    
    def __init__(self):
        """Initialize Gemini embedder"""
        settings = get_settings()
        
        model = getattr(settings, 'GEMINI_MODEL', 'models/text-embedding-004')
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        dimension = 768
        batch_size = 100
        
        super().__init__(
            model_name=model,
            dimension=dimension,
            batch_size=batch_size,
            requires_api_key=True
        )
        
        self.api_key = api_key
        
        # Configure Gemini
        if GENAI_AVAILABLE and self.api_key:
            genai.configure(api_key=self.api_key)
            self.client = genai
        else:
            self.client = None
        
        # Cache
        cache_dir = getattr(settings, 'GEMINI_CACHE_DIR', 'data/embeddings_cache/gemini')
        self.cache = CacheManager(cache_dir=cache_dir, compression=True)
        
        logger.info(f"GeminiEmbedder initialized: {model}")
    
    async def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Embed texts using Gemini API
        
        Args:
            texts: List of texts
            
        Returns:
            List of embeddings
        """
        if not texts:
            return []
        
        if not self.client or not self.api_key:
            logger.warning("Gemini not configured")
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
        
        # Generate embeddings
        new_embeddings = []
        for text in uncached_texts:
            try:
                result = self.client.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="retrieval_document"
                )
                new_embeddings.append(result['embedding'])
                
                # Respect rate limit (15 req/min = 4 seconds between requests)
                time.sleep(0.25)
                
            except Exception as e:
                logger.error(f"Gemini embedding error: {e}")
                new_embeddings.append(None)
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
        """Check if Gemini API is accessible"""
        if not self.client or not self.api_key:
            return False
        
        try:
            result = self.client.embed_content(
                model=self.model_name,
                content="test",
                task_type="retrieval_document"
            )
            return 'embedding' in result
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False