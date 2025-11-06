"""
Tests for Jina AI Embedder
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.rag.embedders.jina_embedder import JinaEmbedder


class TestJinaEmbedder:
    """Test Jina AI embedder"""
    
    @pytest.fixture
    def jina_embedder(self):
        """Create Jina embedder instance"""
        with patch('core.rag.embedders.jina_embedder.CacheManager'):
            return JinaEmbedder()
    
    def test_initialization(self, jina_embedder):
        """Test Jina embedder initialization"""
        assert jina_embedder.model_name == "jina-embeddings-v2-base-en"
        assert jina_embedder.dimension == 768
        assert jina_embedder.requires_api_key == False
        assert jina_embedder.token_limit == 10_000_000
    
    def test_estimate_tokens(self, jina_embedder):
        """Test token estimation"""
        texts = ["hello world", "this is a test"]
        estimated = jina_embedder._estimate_tokens(texts)
        
        # "hello world" = 2 words, "this is a test" = 4 words
        # Total = 6 words * 1.3 = 7.8 ≈ 7 tokens
        assert estimated > 0
        assert estimated < 20  # Rough upper bound
    
    def test_check_token_limit(self, jina_embedder):
        """Test token limit checking"""
        # Within limit
        assert jina_embedder._check_token_limit(1000) == True
        
        # Exceed limit
        jina_embedder.tokens_used = 9_500_000
        assert jina_embedder._check_token_limit(1_000_000) == False
    
    @pytest.mark.asyncio
    async def test_embed_batch_success(self, jina_embedder):
        """Test successful batch embedding"""
        texts = ["test1", "test2"]
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1] * 768},
                {"embedding": [0.2] * 768}
            ],
            "usage": {"total_tokens": 10}
        }
        mock_response.raise_for_status = Mock()
        
        # Mock cache (all misses)
        jina_embedder.cache.get_batch = Mock(return_value=[None, None])
        jina_embedder.cache.set_batch = Mock()
        
        # Mock session
        jina_embedder.session.post = Mock(return_value=mock_response)
        
        # Test
        embeddings = await jina_embedder.embed_batch(texts)
        
        assert len(embeddings) == 2
        assert all(len(emb) == 768 for emb in embeddings)
        assert jina_embedder.tokens_used == 10
    
    @pytest.mark.asyncio
    async def test_embed_batch_with_cache(self, jina_embedder):
        """Test batch embedding with cache hits"""
        texts = ["cached_text", "new_text"]
        
        # Mock cache (first is cached, second is not)
        cached_embedding = [0.5] * 768
        jina_embedder.cache.get_batch = Mock(return_value=[cached_embedding, None])
        jina_embedder.cache.set_batch = Mock()
        
        # Mock HTTP for new text only
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": [0.2] * 768}],
            "usage": {"total_tokens": 5}
        }
        mock_response.raise_for_status = Mock()
        jina_embedder.session.post = Mock(return_value=mock_response)
        
        # Test
        embeddings = await jina_embedder.embed_batch(texts)
        
        assert len(embeddings) == 2
        assert embeddings[0] == cached_embedding
        assert embeddings[1] == [0.2] * 768
        assert jina_embedder.stats.cache_hits == 1
        assert jina_embedder.stats.cache_misses == 1
    
    def test_get_token_usage(self, jina_embedder):
        """Test token usage retrieval"""
        jina_embedder.tokens_used = 5_000_000
        
        usage = jina_embedder.get_token_usage()
        
        assert usage["tokens_used"] == 5_000_000
        assert usage["token_limit"] == 10_000_000
        assert usage["tokens_remaining"] == 5_000_000
        assert usage["percentage_used"] == 50.0