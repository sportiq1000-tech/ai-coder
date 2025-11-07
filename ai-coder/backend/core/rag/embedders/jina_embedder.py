"""
Jina AI Embedder
Primary embedder with 10M free tokens. NOW REQUIRES AN API KEY.
"""

import requests
import time
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from utils.logger import logger
from utils.config import get_settings
from .base_embedder import BaseEmbedder
from .cache_manager import CacheManager


class JinaEmbedder(BaseEmbedder):
    """
    Jina AI embedding implementation.
    
    Features:
    - 10,000,000 free tokens (with API key)
    - No rate limiting
    - 768 dimensions
    - Batch processing (100 texts)
    """
    
    API_URL = "https://api.jina.ai/v1/embeddings"
    
    def __init__(self):
        """Initialize Jina embedder"""
        settings = get_settings()
        
        # FIX: Add API key handling
        model = getattr(settings, 'JINA_MODEL', 'jina-embeddings-v2-base-en')
        api_key = getattr(settings, 'JINA_API_KEY', None)
        dimension = 768  # Jina v2 base is 768-dim
        batch_size = getattr(settings, 'JINA_BATCH_SIZE', 100)
        
        super().__init__(
            model_name=model,
            dimension=dimension,
            batch_size=batch_size,
            requires_api_key=True  # FIX: Changed to True
        )
        
        self.api_key = api_key
        
        # Configuration
        self.cache_dir = getattr(settings, 'JINA_CACHE_DIR', 'data/embeddings_cache/jina')
        self.compression = getattr(settings, 'JINA_COMPRESSION', True)
        self.token_limit = getattr(settings, 'JINA_TOKEN_LIMIT', 10_000_000)
        self.token_warning_threshold = getattr(settings, 'JINA_TOKEN_WARNING_THRESHOLD', 0.8)
        
        # Initialize cache
        self.cache = CacheManager(
            cache_dir=self.cache_dir,
            compression=self.compression
        )
        
        # Token tracking
        self.tokens_used = 0
        self.token_file = Path(self.cache_dir) / "token_usage.json"
        self._load_token_usage()
        
        # HTTP session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        
        # FIX: Add Authorization header if API key exists
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })
            logger.info(f"JinaEmbedder initialized: {model} ({dimension}D)")
        else:
            logger.warning(f"JinaEmbedder initialized without API key. It will not work.")
    
    def _load_token_usage(self):
        """Load token usage from file"""
        if self.token_file.exists():
            try:
                import json
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    self.tokens_used = data.get("tokens_used", 0)
                    logger.info(f"Loaded token usage: {self.tokens_used:,} / {self.token_limit:,}")
            except Exception as e:
                logger.warning(f"Failed to load token usage: {e}")
    
    def _save_token_usage(self):
        """Save token usage to file"""
        try:
            import json
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, 'w') as f:
                json.dump({
                    "tokens_used": self.tokens_used,
                    "last_updated": datetime.now().isoformat(),
                    "limit": self.token_limit,
                    "percentage_used": (self.tokens_used / self.token_limit) * 100 if self.token_limit > 0 else 0
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save token usage: {e}")
    
    def _estimate_tokens(self, texts: List[str]) -> int:
        """
        Estimate token count for texts
        Jina uses ~1.3 tokens per word on average
        """
        total_words = sum(len(text.split()) for text in texts)
        return int(total_words * 1.3)
    
    def _check_token_limit(self, estimated_tokens: int) -> bool:
        """
        Check if we're within token limit
        
        Args:
            estimated_tokens: Tokens needed for request
            
        Returns:
            True if within limit, False otherwise
        """
        if self.tokens_used + estimated_tokens > self.token_limit:
            logger.error(f"Token limit exceeded: {self.tokens_used:,} + {estimated_tokens:,} > {self.token_limit:,}")
            return False
        
        # Warning at threshold
        if self.token_limit > 0:
            usage_after = self.tokens_used + estimated_tokens
            percentage = (usage_after / self.token_limit)
            
            if percentage > self.token_warning_threshold:
                logger.warning(
                    f"Token usage warning: {usage_after:,} / {self.token_limit:,} "
                    f"({percentage*100:.1f}%)"
                )
        
        return True
    
    async def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Embed a batch of texts using Jina AI
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings
        """
        if not texts:
            return []
            
        if not self.api_key:
            logger.error("Jina API key not configured, cannot generate embeddings.")
            self.stats.total_errors += 1
            self.stats.last_error = "API key not configured"
            return [None] * len(texts)
        
        start_time = time.time()
        self.stats.total_requests += 1 # This counts one "embed_batch" call, not API calls
        self.stats.total_texts += len(texts)
        
        # Check cache first
        cached_embeddings = self.cache.get_batch(texts, self.model_name)
        uncached_indices = [i for i, emb in enumerate(cached_embeddings) if emb is None]
        uncached_texts = [texts[i] for i in uncached_indices]
        
        cache_hits = len(texts) - len(uncached_texts)
        self.stats.cache_hits += cache_hits
        self.stats.cache_misses += len(uncached_texts)
        
        if cache_hits > 0:
            logger.info(f"Cache hit: {cache_hits}/{len(texts)} embeddings")
        
        if not uncached_texts:
            return cached_embeddings
        
        # Check token limit for the whole operation
        estimated_tokens = self._estimate_tokens(uncached_texts)
        if not self._check_token_limit(estimated_tokens):
            logger.error("Token limit exceeded, cannot generate embeddings")
            self.stats.total_errors += 1
            return [None] * len(texts)
        
        # FIX: Implement batching loop
        all_new_embeddings = {}
        for i in range(0, len(uncached_texts), self.batch_size):
            batch_texts = uncached_texts[i:i + self.batch_size]
            batch_indices = uncached_indices[i:i + self.batch_size]
            
            try:
                response = self.session.post(
                    self.API_URL,
                    json={
                        "model": self.model_name,
                        "input": batch_texts,
                        "encoding_format": "float"
                    },
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                new_embeddings_for_batch = [item["embedding"] for item in data["data"]]
                
                # Map embeddings back to their original indices
                for original_idx, embedding in zip(batch_indices, new_embeddings_for_batch):
                    all_new_embeddings[original_idx] = embedding

                # Update token usage
                actual_tokens = data.get("usage", {}).get("total_tokens", self._estimate_tokens(batch_texts))
                self.tokens_used += actual_tokens
                self._save_token_usage()
                
                logger.info(
                    f"Processed batch {i//self.batch_size + 1}: "
                    f"{len(batch_texts)} embeddings ({actual_tokens} tokens)"
                )
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Jina API request failed for batch: {e}")
                self.stats.total_errors += 1
                self.stats.last_error = str(e)
                # Mark embeddings for this failed batch as None
                for original_idx in batch_indices:
                    all_new_embeddings[original_idx] = None
            except Exception as e:
                logger.error(f"Unexpected error in Jina embedder batch: {e}")
                self.stats.total_errors += 1
                self.stats.last_error = str(e)
                for original_idx in batch_indices:
                    all_new_embeddings[original_idx] = None

        # Cache all successfully generated embeddings
        successful_texts = [texts[idx] for idx, emb in all_new_embeddings.items() if emb is not None]
        successful_embeddings = [emb for emb in all_new_embeddings.values() if emb is not None]
        if successful_texts:
            self.cache.set_batch(successful_texts, self.model_name, successful_embeddings)

        # Merge cached results and new results
        final_results = list(cached_embeddings)
        for original_idx, embedding in all_new_embeddings.items():
            final_results[original_idx] = embedding
            
        elapsed_ms = (time.time() - start_time) * 1000
        self.stats.average_latency_ms = (
            (self.stats.average_latency_ms * (self.stats.total_requests - 1) + elapsed_ms) 
            / self.stats.total_requests if self.stats.total_requests > 0 else elapsed_ms
        )
        self.stats.last_request_time = datetime.now()

        return final_results
    
    def health_check(self) -> bool:
        """
        Check if Jina API is accessible
        
        Returns:
            True if healthy
        """
        # FIX: Check for API key first
        if not self.api_key:
            return False
            
        try:
            # Test with a simple embedding
            response = self.session.post(
                self.API_URL,
                json={
                    "model": self.model_name,
                    "input": ["test"],
                    "encoding_format": "float"
                },
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Jina health check failed: {e}")
            return False
    
    def get_token_usage(self) -> Dict[str, Any]:
        """
        Get token usage statistics
        
        Returns:
            Token usage info
        """
        return {
            "tokens_used": self.tokens_used,
            "token_limit": self.token_limit,
            "tokens_remaining": self.token_limit - self.tokens_used,
            "percentage_used": (self.tokens_used / self.token_limit) * 100 if self.token_limit > 0 else 0,
            "warning_threshold": self.token_warning_threshold * 100
        }
    
    def __del__(self):
        """Cleanup on destruction"""
        if hasattr(self, 'session'):
            self.session.close()