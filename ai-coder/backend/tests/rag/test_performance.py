"""
Performance tests for the new embedding strategy
"""

import pytest
import time
import requests
from core.rag.embedders.jina_embedder import JinaEmbedder
from unittest.mock import patch, Mock, MagicMock


@pytest.mark.slow
class TestEmbeddingPerformance:
    """Performance benchmarks for embedders"""
    
    @pytest.fixture
    def jina_embedder(self):
        """Create a Jina embedder with mocked API for performance testing"""
        with patch('core.rag.embedders.jina_embedder.CacheManager') as mock_cache:
            embedder = JinaEmbedder()
            
            mock_session = MagicMock(spec=requests.Session)
            
            def mock_post_side_effect(*args, **kwargs):
                # FIX: Correctly access the input texts from the call arguments
                input_texts = kwargs.get('json', {}).get('input', [])
                
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "data": [{"embedding": [0.1] * 768} for _ in input_texts],
                    "usage": {"total_tokens": len(input_texts) * 2} # Simulate token usage
                }
                mock_response.raise_for_status = Mock()
                return mock_response
                
            mock_session.post.side_effect = mock_post_side_effect
            embedder.session = mock_session
            
            # FIX: Make the cache mock dynamic based on input size
            def mock_get_batch(texts, model):
                return [None] * len(texts)
                
            mock_cache.return_value.get_batch = mock_get_batch
            mock_cache.return_value.set_batch = Mock()
            
            # Reset state for each test
            embedder.tokens_used = 0
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
        
        # Mock cache to return hits for the second call
        jina_embedder.cache.get_batch.return_value = [[0.1] * 768] * 100
        
        # Second call (cache hit)
        start_hit = time.time()
        await jina_embedder.embed_batch(texts)
        duration_hit = time.time() - start_hit
        
        print(f"\nCache miss time: {duration_miss:.4f}s")
        print(f"Cache hit time: {duration_hit:.4f}s")
        
        assert duration_hit < duration_miss / 10
        assert duration_hit < 0.05  # Should be extremely fast