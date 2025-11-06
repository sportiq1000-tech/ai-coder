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
            # Mock the return value of the smart embedder's method
            mock_instance.embed_chunks = Mock(
                return_value=[
                    CodeChunk(
                        **chunks[0].model_dump(),
                        embedding=[0.1] * 768
                    )
                ]
            )
            mock_smart_embedder_class.return_value = mock_instance
            
            # Use the public-facing CodeEmbedder
            embedder = CodeEmbedder()
            result_chunks = await embedder.embed_chunks(chunks)
            
            # Verify the SmartEmbedder was called and the result is correct
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
        text = "This is a simple test text with seven words."
        
        # New estimation is 1.3 tokens per word (7 * 1.3 = 9.1 -> 9)
        # Old estimation was len(text) // 4 = 49 // 4 = 12
        # The new estimation is more realistic for modern tokenizers
        estimated_tokens = embedder.count_tokens(text)
        
        assert estimated_tokens == int(7 * 1.3)
    
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