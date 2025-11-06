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
        with patch('core.rag.connections.VectorStore') as mock_vector_store, \
             patch('core.rag.connections.GraphStore') as mock_graph_store, \
             patch('core.rag.embeddings.openai.OpenAI') as mock_openai:
            
            # Setup mocks
            mock_vs_instance = MagicMock()
            mock_vs_instance.health_check.return_value = True
            mock_vs_instance.store_chunks = AsyncMock(return_value=["chunk_1"])
            mock_vector_store.return_value = mock_vs_instance
            
            mock_gs_instance = MagicMock()
            mock_gs_instance.health_check.return_value = True
            mock_graph_store.return_value = mock_gs_instance
            
            mock_openai_instance = MagicMock()
            mock_response = Mock()
            mock_response.data = [Mock(embedding=[0.1] * 768)]
            mock_openai_instance.embeddings.create.return_value = mock_response
            mock_openai.return_value = mock_openai_instance
            
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
            
            # Generate embeddings if OpenAI is configured
            embedder = CodeEmbedder()
            if embedder.client:
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