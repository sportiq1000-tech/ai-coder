"""
Performance tests for the new embedding strategy
"""

import pytest
import time
from core.rag.embedders.jina_embedder import JinaEmbedder
from unittest.mock import patch, Mock


@pytest.mark.slow
class TestEmbeddingPerformance:
    """Performance benchmarks for embedders"""
    
    @pytest.fixture
    def jina_embedder(self):
        """Create a Jina embedder with mocked API for performance testing"""
        with patch('core.rag.embedders.jina_embedder.CacheManager'):
            embedder = JinaEmbedder()
            
            # Mock the session post method to return a valid response quickly
            mock_response = Mock()
            mock_response.status_code = 200
            
            def mock_json():
                # Simulate a dynamic response based on input size
                return {
                    "data": [{"embedding": [0.1] * 768} for _ in range(embedder.session.post.call_args.json['input'].__len__())],
                    "usage": {"total_tokens": 100}
                }
            
            mock_response.json = mock_json
            mock_response.raise_for_status = Mock()
            embedder.session.post = Mock(return_value=mock_response)
            
            # Mock cache to simulate all misses
            embedder.cache.get_batch = Mock(return_value=[None] * 1000)
            embedder.cache.set_batch = Mock()
            
            return embedder
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("num_chunks, expected_time_s", [
        (10, 0.5),    # Expected to be very fast
        (100, 2.0),   # Should be around 1.5-2s
        (500, 8.0),   # Should be around 7-8s
        (1000, 16.0)  # Should be around 15-16s
    ])
    async def test_jina_batch_performance(self, jina_embedder, num_chunks, expected_time_s):
        """Benchmark Jina embedder batch processing time"""
        texts = [f"This is test chunk number {i}" for i in range(num_chunks)]
        
        start_time = time.time()
        await jina_embedder.embed_batch(texts)
        end_time = time.time()
        
        duration = end_time - start_time
        
        print(f"\nProcessed {num_chunks} chunks in {duration:.2f}s (expected < {expected_time_s}s)")
        
        # Assert that the performance is within a reasonable range
        assert duration < expected_time_s
        
        # Verify number of API calls
        num_api_calls = jina_embedder.session.post.call_count
        expected_calls = (num_chunks + jina_embedder.batch_size - 1) // jina_embedder.batch_size
        
        assert num_api_calls == expected_calls
    
    @pytest.mark.asyncio
    async def test_cache_performance(self, jina_embedder):
        """Benchmark cache hit performance"""
        texts = ["this text will be cached"] * 100
        
        # First call (cache miss)
        start_miss = time.time()
        await jina_embedder.embed_batch(texts)
        duration_miss = time.time() - start_miss
        
        # Mock cache to return hits
        jina_embedder.cache.get_batch = Mock(return_value=[[0.1] * 768] * 100)
        
        # Second call (cache hit)
        start_hit = time.time()
        await jina_embedder.embed_batch(texts)
        duration_hit = time.time() - start_hit
        
        print(f"\nCache miss time: {duration_miss:.4f}s")
        print(f"Cache hit time: {duration_hit:.4f}s")
        
        # Cache hit should be orders of magnitude faster
        assert duration_hit < duration_miss / 10
        assert duration_hit < 0.05  # Should be extremely fast