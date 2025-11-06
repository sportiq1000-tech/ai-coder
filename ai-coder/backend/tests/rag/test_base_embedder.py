"""
Tests for Base Embedder Abstract Class
"""

import pytest
from core.rag.embedders.base_embedder import BaseEmbedder, EmbedderStats


class MockEmbedder(BaseEmbedder):
    """Mock embedder for testing"""
    
    def __init__(self):
        super().__init__(
            model_name="mock-model",
            dimension=768,
            batch_size=100,
            requires_api_key=False
        )
    
    async def embed_batch(self, texts):
        return [[0.1] * self.dimension for _ in texts]
    
    def health_check(self):
        return True


class TestBaseEmbedder:
    """Test base embedder functionality"""
    
    def test_initialization(self):
        """Test embedder initialization"""
        embedder = MockEmbedder()
        
        assert embedder.model_name == "mock-model"
        assert embedder.dimension == 768
        assert embedder.batch_size == 100
        assert embedder.requires_api_key == False
        assert isinstance(embedder.stats, EmbedderStats)
    
    @pytest.mark.asyncio
    async def test_embed_single(self):
        """Test single text embedding"""
        embedder = MockEmbedder()
        embedding = await embedder.embed_single("test text")
        
        assert embedding is not None
        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)
    
    def test_pad_or_truncate(self):
        """Test dimension adjustment"""
        embedder = MockEmbedder()
        
        # Test padding
        short_emb = [0.1] * 384
        padded = embedder._pad_or_truncate(short_emb, 768)
        assert len(padded) == 768
        assert padded[:384] == short_emb
        assert padded[384:] == [0.0] * 384
        
        # Test truncation
        long_emb = [0.1] * 1536
        truncated = embedder._pad_or_truncate(long_emb, 768)
        assert len(truncated) == 768
        
        # Test no change
        correct_emb = [0.1] * 768
        unchanged = embedder._pad_or_truncate(correct_emb, 768)
        assert len(unchanged) == 768
        assert unchanged == correct_emb
    
    def test_get_stats(self):
        """Test statistics retrieval"""
        embedder = MockEmbedder()
        stats = embedder.get_stats()
        
        assert "model_name" in stats
        assert "dimension" in stats
        assert "batch_size" in stats
        assert "total_requests" in stats
        assert stats["model_name"] == "mock-model"
        assert stats["dimension"] == 768
    
    def test_reset_stats(self):
        """Test statistics reset"""
        embedder = MockEmbedder()
        embedder.stats.total_requests = 10
        embedder.stats.total_errors = 5
        
        embedder.reset_stats()
        
        assert embedder.stats.total_requests == 0
        assert embedder.stats.total_errors == 0