"""
Tests for Vector Store implementation
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from core.rag.vector_store import VectorStore
from schemas.rag_schemas import CodeChunk, SearchResult

class TestVectorStore:
    """Test vector store operations"""
    
    @pytest.fixture
    def vector_store(self):
        """Create vector store instance for testing"""
        with patch('core.rag.vector_store.QdrantClient'):
            store = VectorStore()
            store.client = MagicMock()
            store.client.get_collections = Mock(return_value=[])
            store.client.collection_exists = Mock(return_value=True)
            return store
    
    @pytest.fixture
    def sample_chunks(self):
        """Create sample code chunks for testing"""
        return [
            CodeChunk(
                id="test_chunk_1",
                content="def hello_world():\n    print('Hello, World!')",
                file_path="test.py",
                language="python",
                chunk_type="function",
                start_line=1,
                end_line=2,
                embedding=[0.1] * 1536,
                metadata={"name": "hello_world"}
            ),
            CodeChunk(
                id="test_chunk_2",
                content="def add(a, b):\n    return a + b",
                file_path="math.py",
                language="python",
                chunk_type="function",
                start_line=1,
                end_line=2,
                embedding=[0.2] * 1536,
                metadata={"name": "add"}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_store_chunks(self, vector_store, sample_chunks):
        """Test storing chunks in vector store"""
        vector_store.client.upsert = Mock(return_value=Mock(operation_id="test_op"))
        
        result = await vector_store.store_chunks(sample_chunks)
        
        # FIX: Check against the expected UUIDs, not the original string IDs.
        expected_id_1 = str(uuid.uuid5(uuid.NAMESPACE_DNS, sample_chunks[0].id))
        expected_id_2 = str(uuid.uuid5(uuid.NAMESPACE_DNS, sample_chunks[1].id))
        
        assert len(result) == 2
        assert expected_id_1 in result
        assert expected_id_2 in result
        vector_store.client.upsert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_chunks(self, vector_store):
        """Test searching chunks in vector store"""
        mock_results = [
            Mock(
                id="test_chunk_1", 
                score=0.9, 
                payload={
                    "content": "def hello_world():",
                    "file_path": "test.py",
                    "language": "python",
                    "chunk_type": "function",
                    "start_line": 1,
                    "end_line": 2,
                    "metadata": {"name": "hello_world"}
                }
            )
        ]
        
        vector_store.client.search = Mock(return_value=mock_results)
        
        query_vector = [0.1] * 1536
        results = await vector_store.search(query_vector)
        
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].id == "test_chunk_1"
        assert results[0].score == 0.9
    
    @pytest.mark.asyncio
    async def test_delete_by_file_path(self, vector_store):
        """Test deleting chunks by file path"""
        vector_store.client.delete = Mock()
        
        await vector_store.delete_by_file_path("test.py")
        
        vector_store.client.delete.assert_called_once()
    
    def test_health_check(self, vector_store):
        """Test health check functionality"""
        vector_store.client.get_collections = Mock(return_value=[])
        assert vector_store.health_check() == True
        
        vector_store.client.get_collections.side_effect = Exception("Connection failed")
        assert vector_store.health_check() == False