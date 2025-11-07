"""
Integration tests for RAG components
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from core.rag.connections import ConnectionManager
from core.rag.chunker import CodeChunker
from core.rag.embeddings import CodeEmbedder

class TestRAGIntegration:
    """Test integration between RAG components"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_processing(self):
        """Test complete pipeline from file to storage"""
        # FIX: Remove the patch for 'core.rag.embeddings.openai.OpenAI'
        # and patch the new SmartEmbedder instead.
        with patch('core.rag.connections.VectorStore') as mock_vector_store, \
             patch('core.rag.connections.GraphStore') as mock_graph_store, \
             patch('core.rag.embedders.smart_embedder.SmartEmbedder') as mock_smart_embedder:

            # Setup mocks for embedder
            mock_embedder_instance = Mock()
            async def mock_embed(chunks):
                for chunk in chunks:
                    chunk.embedding = [0.1] * 768
                return chunks
            mock_smart_embedder.return_value.embed_chunks = mock_embed
            
            # ... (rest of the mocks are fine)
            
            mock_vs_instance = MagicMock()
            mock_vs_instance.health_check.return_value = True
            mock_vs_instance.store_chunks = AsyncMock(return_value=["chunk_1"])
            mock_vector_store.return_value = mock_vs_instance
            
            mock_gs_instance = MagicMock()
            mock_gs_instance.health_check.return_value = True
            mock_graph_store.return_value = mock_gs_instance
            
            # FIX: Create test data with sufficient length (> 50 chars)
            test_code = '''
def test_function():
    """A test function that does something"""
    result = "Hello, World!"
    return result

class TestClass:
    """A test class"""
    
    def method(self):
        return "test"
'''
            
            # Process file
            chunker = CodeChunker()
            chunks = await chunker.chunk_file("test.py", test_code, "python")
            assert len(chunks) > 0, "Should create at least one chunk"
            
            # Generate embeddings
            embedder = CodeEmbedder() # This will use the mocked SmartEmbedder
            chunks_with_embeddings = await embedder.embed_chunks(chunks)
            
            assert all(chunk.embedding is not None for chunk in chunks_with_embeddings)
    
    @pytest.mark.asyncio
    async def test_connection_manager_initialization(self):
        """Test connection manager initialization"""
        with patch('core.rag.connections.VectorStore') as mock_vector_store, \
             patch('core.rag.connections.GraphStore') as mock_graph_store:
            
            # Setup mocks
            mock_vs_instance = MagicMock()
            mock_vs_instance.health_check.return_value = True
            mock_vector_store.return_value = mock_vs_instance
            
            mock_gs_instance = MagicMock()
            mock_gs_instance.health_check.return_value = True
            mock_graph_store.return_value = mock_gs_instance
            
            # Initialize connection manager
            manager = ConnectionManager()
            await manager.initialize()
            
            # Verify connections were created
            assert manager.vector_store is not None
            
            # Cleanup
            await manager.cleanup()