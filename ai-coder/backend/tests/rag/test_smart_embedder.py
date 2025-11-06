"""
Tests for Smart Embedder with Fallback Logic
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from core.rag.embedders.smart_embedder import SmartEmbedder
from schemas.rag_schemas import CodeChunk


class TestSmartEmbedder:
    """Test smart embedder orchestration"""
    
    @pytest.fixture
    def mock_embedders(self):
        """Create mock embedders"""
        mock_jina = Mock()
        mock_jina.__class__.__name__ = "JinaEmbedder"
        mock_jina.embed_batch = AsyncMock(return_value=[[0.1] * 768, [0.2] * 768])
        mock_jina.embed_single = AsyncMock(return_value=[0.1] * 768)
        mock_jina.health_check = Mock(return_value=True)
        mock_jina.get_stats = Mock(return_value={"requests": 0})
        
        mock_hf = Mock()
        mock_hf.__class__.__name__ = "HuggingFaceEmbedder"
        mock_hf.embed_batch = AsyncMock(return_value=[[0.3] * 768, [0.4] * 768])
        mock_hf.embed_single = AsyncMock(return_value=[0.3] * 768)
        mock_hf.health_check = Mock(return_value=True)
        mock_hf.get_stats = Mock(return_value={"requests": 0})
        
        return mock_jina, mock_hf
    
    @pytest.mark.asyncio
    async def test_primary_success(self, mock_embedders):
        """Test successful embedding with primary embedder"""
        mock_jina, mock_hf = mock_embedders
        
        with patch('core.rag.embedders.smart_embedder.JinaEmbedder', return_value=mock_jina), \
             patch('core.rag.embedders.smart_embedder.HuggingFaceEmbedder', return_value=mock_hf):
            
            embedder = SmartEmbedder()
            
            chunks = [
                CodeChunk(
                    content="def test(): pass",
                    file_path="test.py",
                    language="python",
                    chunk_type="function",
                    start_line=1,
                    end_line=1
                )
            ]
            
            result = await embedder.embed_chunks(chunks)
            
            assert len(result) == 1
            assert result[0].embedding is not None
            assert len(result[0].embedding) == 768
            
            # Verify primary was called
            mock_jina.embed_batch.assert_called_once()
            mock_hf.embed_batch.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self, mock_embedders):
        """Test fallback when primary fails"""
        mock_jina, mock_hf = mock_embedders
        
        # Make primary fail
        mock_jina.embed_batch = AsyncMock(side_effect=Exception("API down"))
        
        with patch('core.rag.embedders.smart_embedder.JinaEmbedder', return_value=mock_jina), \
             patch('core.rag.embedders.smart_embedder.HuggingFaceEmbedder', return_value=mock_hf), \
             patch('core.rag.embedders.smart_embedder.GeminiEmbedder') as mock_gemini_class, \
             patch('core.rag.embedders.smart_embedder.LocalEmbedder') as mock_local_class:
            
            # Mock other embedders not available
            mock_gemini_class.return_value.health_check.return_value = False
            mock_local_class.return_value.health_check.return_value = False
            
            embedder = SmartEmbedder()
            
            chunks = [
                CodeChunk(
                    content="def test(): pass",
                    file_path="test.py",
                    language="python",
                    chunk_type="function",
                    start_line=1,
                    end_line=1
                )
            ]
            
            result = await embedder.embed_chunks(chunks)
            
            # Verify fallback was called
            mock_jina.embed_batch.assert_called_once()
            mock_hf.embed_batch.assert_called_once()
            
            assert result[0].embedding is not None
    
    @pytest.mark.asyncio
    async def test_all_embedders_fail(self):
        """Test behavior when all embedders fail"""
        with patch('core.rag.embedders.smart_embedder.JinaEmbedder') as mock_jina_class, \
             patch('core.rag.embedders.smart_embedder.HuggingFaceEmbedder') as mock_hf_class, \
             patch('core.rag.embedders.smart_embedder.GeminiEmbedder') as mock_gemini_class, \
             patch('core.rag.embedders.smart_embedder.LocalEmbedder') as mock_local_class:
            
            # Make all health checks fail
            for mock_class in [mock_jina_class, mock_hf_class, mock_gemini_class, mock_local_class]:
                mock_instance = Mock()
                mock_instance.health_check.return_value = False
                mock_class.return_value = mock_instance
            
            # This should handle gracefully
            embedder = SmartEmbedder()
            
            # Embedder should have at least tried to initialize something
            assert embedder is not None