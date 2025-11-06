"""
Tests for the Embedding Cache Manager
"""

import pytest
import time
from pathlib import Path
from core.rag.embedders.cache_manager import CacheManager


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory for tests"""
    return tmp_path / "test_cache"


class TestCacheManager:
    """Test the CacheManager functionality"""
    
    def test_initialization(self, temp_cache_dir):
        """Test cache manager initialization"""
        cache = CacheManager(cache_dir=str(temp_cache_dir))
        assert cache.cache_dir.exists()
        assert cache.metadata_file.exists()
        assert cache.metadata["total_entries"] == 0
    
    def test_set_and_get(self, temp_cache_dir):
        """Test setting and getting a single cache entry"""
        cache = CacheManager(cache_dir=str(temp_cache_dir))
        text = "hello world"
        model = "test-model"
        embedding = [0.1, 0.2, 0.3]
        
        # Should be a cache miss first
        assert cache.get(text, model) is None
        
        # Set the embedding
        cache.set(text, model, embedding)
        
        # Should be a cache hit now
        retrieved = cache.get(text, model)
        assert retrieved == embedding
    
    def test_compression(self, temp_cache_dir):
        """Test cache compression"""
        # Test with compression
        compressed_cache_dir = temp_cache_dir / "compressed"
        compressed_cache = CacheManager(cache_dir=str(compressed_cache_dir), compression=True)
        
        # Test without compression
        uncompressed_cache_dir = temp_cache_dir / "uncompressed"
        uncompressed_cache = CacheManager(cache_dir=str(uncompressed_cache_dir), compression=False)
        
        text = "a" * 1000
        model = "test-model"
        embedding = [0.1] * 768
        
        compressed_cache.set(text, model, embedding)
        uncompressed_cache.set(text, model, embedding)
        
        compressed_size = compressed_cache.get_stats()["total_size_mb"]
        uncompressed_size = uncompressed_cache.get_stats()["total_size_mb"]
        
        # Compressed should be significantly smaller
        assert compressed_size > 0
        assert uncompressed_size > 0
        assert compressed_size < uncompressed_size
    
    def test_ttl_expiration(self, temp_cache_dir):
        """Test that cache entries expire after TTL"""
        # Create a cache with a very short TTL (1 second)
        cache = CacheManager(cache_dir=str(temp_cache_dir), ttl_days=1/86400)
        
        text = "this will expire"
        model = "test-model"
        embedding = [0.4, 0.5, 0.6]
        
        cache.set(text, model, embedding)
        assert cache.get(text, model) == embedding
        
        # Wait for TTL to expire
        time.sleep(1.1)
        
        # Should now be a cache miss
        assert cache.get(text, model) is None
    
    def test_cache_clearing(self, temp_cache_dir):
        """Test clearing the cache"""
        cache = CacheManager(cache_dir=str(temp_cache_dir))
        
        cache.set("text1", "model1", [0.1])
        cache.set("text2", "model2", [0.2])
        
        assert cache.get_stats()["total_entries"] > 0
        
        cache.clear()
        
        assert cache.get_stats()["total_entries"] == 0
        assert cache.get_stats()["total_size_mb"] == 0
        assert cache.get("text1", "model1") is None
    
    def test_batch_operations(self, temp_cache_dir):
        """Test batch set and get operations"""
        cache = CacheManager(cache_dir=str(temp_cache_dir))
        
        texts = ["batch1", "batch2"]
        model = "batch-model"
        embeddings = [[0.1], [0.2]]
        
        # Set batch
        cache.set_batch(texts, model, embeddings)
        
        # Get batch
        retrieved = cache.get_batch(texts, model)
        assert retrieved == embeddings
        
        # Test with partial cache miss
        retrieved_partial = cache.get_batch(["batch1", "not_cached"], model)
        assert retrieved_partial[0] == [0.1]
        assert retrieved_partial[1] is None