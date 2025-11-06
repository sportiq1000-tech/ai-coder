"""
Local Sentence Transformers Embedder
Final fallback that always works (offline)
"""

import time
from typing import List, Optional
from datetime import datetime
from utils.logger import logger
from utils.config import get_settings
from .base_embedder import BaseEmbedder
from .cache_manager import CacheManager

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not installed, local embedder unavailable")


class LocalEmbedder(BaseEmbedder):
    """
    Local embedding using Sentence Transformers
    
    Features:
    - Works offline
    - No API key needed
    - ~500MB RAM usage when loaded
    - 384 dimensions (padded to 768)
    """
    
    def __init__(self):
        """Initialize local embedder"""
        settings = get_settings()
        
        model = getattr(settings, 'LOCAL_MODEL', 'paraphrase-MiniLM-L3-v2')
        dimension = 768  # Padded from 384
        batch_size = 32  # Smaller batches for RAM efficiency
        
        super().__init__(
            model_name=model,
            dimension=dimension,
            batch_size=batch_size,
            requires_api_key=False
        )
        
        self.native_dimension = 384
        self.model = None
        
        # Lazy load model (only when needed)
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            self._load_model()
        
        # Cache
        cache_dir = getattr(settings, 'LOCAL_CACHE_DIR', 'data/embeddings_cache/local')
        self.cache = CacheManager(cache_dir=cache_dir, compression=True)
        
        logger.info(f"LocalEmbedder initialized: {model}")
    
    def _load_model(self):
        """Lazy load the model"""
        if self.model is None and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                logger.info(f"Loading local model: {self.model_name}")
                self.model = SentenceTransformer(self.model_name)
                logger.info("Local model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load local model: {e}")
                self.model = None
    
    async def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Embed texts using local model
        
        Args:
            texts: List of texts
            
        Returns:
            List of embeddings (padded to 768-dim)
        """
        if not texts:
            return []
        
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.error("sentence-transformers not available")
            return [None] * len(texts)
        
        # Load model if not already loaded
        if self.model is None:
            self._load_model()
        
        if self.model is None:
            logger.error("Failed to load local model")
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
        try:
            embeddings_raw = self.model.encode(
                uncached_texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            # Convert to list and pad to 768 dimensions
            new_embeddings = [
                self._pad_or_truncate(emb.tolist(), self.dimension)
                for emb in embeddings_raw
            ]
            
            logger.info(f"Generated {len(new_embeddings)} embeddings locally")
            
        except Exception as e:
            logger.error(f"Local embedding failed: {e}")
            new_embeddings = [None] * len(uncached_texts)
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
        """Check if local model is loaded"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return False
        
        if self.model is None:
            self._load_model()
        
        return self.model is not None