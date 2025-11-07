"""
Tests to ensure the new SmartEmbedder is compatible with the existing system
"""

import pytest
from unittest.mock import Mock, patch
from core.rag.embeddings import CodeEmbedder  # The public-facing class
from schemas.rag_schemas import CodeChunk


class TestEmbeddingMigration:
    """Test compatibility of the new embedding system"""
    
    def test_code_embedder_uses_smart_embedder(self):
        """Verify that CodeEmbedder initializes and uses SmartEmbedder"""
        with patch('core.rag.embeddings.SmartEmbedder') as mock_smart_embedder_class:
            mock_instance = Mock()
            mock_smart_embedder_class.return_value = mock_instance
            
            embedder = CodeEmbedder()
            
            assert embedder.embedder is mock_instance
            mock_smart_embedder_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_embed_chunks_api_compatibility(self):
        """Test that embed_chunks maintains its API signature and behavior"""
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
        
        with patch('core.rag.embeddings.SmartEmbedder') as mock_smart_embedder_class:
            mock_instance = Mock()
            
            # FIX: Create a new chunk for the return value
            # instead of unpacking and overwriting.
            return_chunk = chunks[0].model_copy(deep=True)
            return_chunk.embedding = [0.1] * 768
            
            mock_instance.embed_chunks = Mock(return_value=[return_chunk])
            mock_smart_embedder_class.return_value = mock_instance
            
            embedder = CodeEmbedder()
            result_chunks = await embedder.embed_chunks(chunks)
            
            mock_instance.embed_chunks.assert_called_once_with(chunks)
            assert len(result_chunks) == 1
            assert result_chunks[0].embedding is not None
            assert len(result_chunks[0].embedding) == 768
    
    @pytest.mark.asyncio
    async def test_embed_query_api_compatibility(self):
        """Test that embed_query maintains its API signature"""
        query = "find all functions"
        
        with patch('core.rag.embeddings.SmartEmbedder') as mock_smart_embedder_class:
            mock_instance = Mock()
            mock_instance.embed_query = Mock(return_value=[0.2] * 768)
            mock_smart_embedder_class.return_value = mock_instance
            
            embedder = CodeEmbedder()
            result_vector = await embedder.embed_query(query)
            
            mock_instance.embed_query.assert_called_once_with(query)
            assert isinstance(result_vector, list)
            assert len(result_vector) == 768
    
    def test_count_tokens_compatibility(self):
        """Test that the new token counting method works"""
        embedder = CodeEmbedder()
        # FIX: The original text had 8 words. Let's use a clear 10-word sentence.
        text = "This is a simple test text with exactly ten words here."
        
        estimated_tokens = embedder.count_tokens(text)
        
        # 10 words * 1.3 = 13.0, which int() makes 13
        assert estimated_tokens == int(10 * 1.3)
    
    @pytest.mark.asyncio
    async def test_graceful_failure(self):
        """Test that if SmartEmbedder fails, chunks are returned unmodified"""
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
        
        with patch('core.rag.embeddings.SmartEmbedder') as mock_smart_embedder_class:
            mock_instance = Mock()
            # Simulate a complete failure
            mock_instance.embed_chunks = Mock(side_effect=Exception("All embedders failed"))
            mock_smart_embedder_class.return_value = mock_instance
            
            embedder = CodeEmbedder()
            result_chunks = await embedder.embed_chunks(chunks)
            
            # Should return original chunks without embeddings
            assert len(result_chunks) == 1
            assert result_chunks[0].embedding is None