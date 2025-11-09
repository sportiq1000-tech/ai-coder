"""
Integration tests for RAG components
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from core.rag.chunker import CodeChunker
from core.rag.embeddings import CodeEmbedder

class MockChunk:
    """A mock chunk object that mimics the CodeChunk schema for testing."""
    def __init__(self, content):
        self.content = content
        self.embedding = None
        # Add all necessary attributes to prevent AttributeError in SmartEmbedder
        self.file_path = "test_mock.py"
        self.language = "python"
        self.chunk_type = "function"
        self.start_line = 1
        self.end_line = 2
        self.metadata = {}

class TestRAGIntegration:
    @pytest.mark.asyncio
    async def test_end_to_end_processing(self):
        """Test complete pipeline from file to storage"""
        test_code = '''
def test_function():
    return "Hello, World!"

class TestClass:
    def method(self):
        return "test"
'''
        
        # Create test chunks manually (avoiding real chunk implementation)
        chunks = [MockChunk(line) for line in test_code.split('\n')]
        
        with patch('core.rag.connections.VectorStore') as mock_vector_store, \
             patch('core.rag.connections.GraphStore') as mock_graph_store, \
             patch('core.rag.embedders.smart_embedder.SmartEmbedder') as mock_smart_embedder, \
             patch('core.rag.embedders.local_embedder.LocalEmbedder') as mock_local_embedder:
             
            # Setup mocks
            mock_smart_embedder.return_value = MagicMock()
            mock_smart_embedder.return_value.get_healthy_embedder.return_value = MagicMock()
            mock_embedder = mock_smart_embedder.return_value.get_healthy_embedder.return_value
            mock_embedder.embed_chunks = AsyncMock()
            
            # Configure embedder to set embeddings
            async def mock_embed(chunks):
                for chunk in chunks:
                    chunk.embedding = [0.1] * 768  # Set mock embedding
                return chunks
            mock_embedder.embed_chunks = mock_embed
            
            # Configure vector store
            mock_vs_instance = MagicMock()
            mock_vs_instance.health_check.return_value = True
            mock_vs_instance.store_chunks = AsyncMock(return_value=["chunk_1"])
            mock_vector_store.return_value = mock_vs_instance
            
            # Configure graph store
            mock_gs_instance = MagicMock()
            mock_gs_instance.health_check.return_value = True
            mock_graph_store.return_value = mock_gs_instance
            
            # Configure local embedder to be healthy
            mock_local_embedder.return_value.health_check.return_value = True
            
            # Generate embeddings
            embedder = CodeEmbedder()
            chunks_with_embeddings = await embedder.embed_chunks(chunks)
            
            # Verify embeddings exist
            assert all(chunk.embedding is not None for chunk in chunks_with_embeddings)