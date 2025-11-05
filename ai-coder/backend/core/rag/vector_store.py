"""
Vector Store Implementation using Qdrant
Handles storage and retrieval of code embeddings
"""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import numpy as np
from utils.logger import logger
from utils.config import get_settings
from schemas.rag_schemas import CodeChunk, SearchResult

class VectorStore:
    """
    Manages vector storage and retrieval operations with Qdrant
    """
    
    def __init__(self):
        """Initialize Qdrant client and collections"""
        self.settings = get_settings()
        self.client = None
        self.collections = {
            "code_embeddings": "code_chunks",
            "documentation": "doc_chunks",
            "bug_patterns": "bug_chunks"
        }
        self._initialize_client()
        self._create_collections()
    
    def _initialize_client(self):
        """Initialize Qdrant client with authentication"""
        try:
            qdrant_url = getattr(self.settings, 'qdrant_url', None)
            qdrant_api_key = getattr(self.settings, 'qdrant_api_key', None)
            
            if not qdrant_url:
                logger.warning("QDRANT_URL not configured, using in-memory storage")
                self.client = QdrantClient(":memory:")
            else:
                self.client = QdrantClient(
                    url=qdrant_url,
                    api_key=qdrant_api_key,
                    timeout=30
                )
            
            # Test connection
            self.client.get_collections()
            logger.info("Qdrant client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            raise
    
    def _create_collections(self):
        """Create collections if they don't exist"""
        embedding_dim = getattr(self.settings, 'embedding_dimension', 1536)
        
        for collection_name in self.collections.values():
            try:
                if not self.client.collection_exists(collection_name):
                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=embedding_dim,
                            distance=Distance.COSINE
                        )
                    )
                    # Create payload indexes
                    self.client.create_payload_index(
                        collection_name=collection_name,
                        field_name="language",
                        field_schema="keyword"
                    )
                    self.client.create_payload_index(
                        collection_name=collection_name,
                        field_name="file_path",
                        field_schema="text"
                    )
                    logger.info(f"Created collection: {collection_name}")
            except Exception as e:
                logger.error(f"Failed to create collection {collection_name}: {e}")
    
    async def store_chunks(
        self, 
        chunks: List[CodeChunk], 
        collection_type: str = "code_embeddings"
    ) -> List[str]:
        """
        Store code chunks in vector store
        
        Args:
            chunks: List of code chunks with embeddings
            collection_type: Type of collection to store in
            
        Returns:
            List of point IDs
        """
        collection_name = self.collections.get(collection_type)
        if not collection_name:
            raise ValueError(f"Unknown collection type: {collection_type}")
        
        points = []
        for i, chunk in enumerate(chunks):
            if not chunk.embedding:
                logger.warning(f"Chunk {chunk.id} has no embedding, skipping")
                continue
                
            point = PointStruct(
                id=chunk.id or f"{chunk.file_path}_{chunk.start_line}_{i}",
                vector=chunk.embedding,
                payload={
                    "content": chunk.content,
                    "file_path": chunk.file_path,
                    "language": chunk.language,
                    "chunk_type": chunk.chunk_type,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "metadata": chunk.metadata
                }
            )
            points.append(point)
        
        if not points:
            logger.warning("No valid points to store")
            return []
        
        try:
            operation_info = self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"Stored {len(points)} chunks in {collection_name}")
            return [str(point.id) for point in points]
        except Exception as e:
            logger.error(f"Failed to store chunks: {e}")
            raise
    
    async def search(
        self, 
        query_vector: List[float], 
        collection_type: str = "code_embeddings",
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for similar code chunks
        
        Args:
            query_vector: Query embedding
            collection_type: Type of collection to search
            limit: Maximum number of results
            filters: Optional filters to apply
            
        Returns:
            List of search results
        """
        collection_name = self.collections.get(collection_type)
        if not collection_name:
            raise ValueError(f"Unknown collection type: {collection_type}")
        
        # Build filter if provided
        query_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            query_filter = Filter(must=conditions)
        
        try:
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            results = []
            for scored_point in search_result:
                result = SearchResult(
                    id=str(scored_point.id),
                    content=scored_point.payload["content"],
                    file_path=scored_point.payload["file_path"],
                    language=scored_point.payload["language"],
                    chunk_type=scored_point.payload["chunk_type"],
                    start_line=scored_point.payload["start_line"],
                    end_line=scored_point.payload["end_line"],
                    score=scored_point.score,
                    metadata=scored_point.payload.get("metadata", {})
                )
                results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    async def delete_by_file_path(
        self, 
        file_path: str, 
        collection_type: str = "code_embeddings"
    ):
        """Delete all chunks from a specific file"""
        collection_name = self.collections.get(collection_type)
        if not collection_name:
            raise ValueError(f"Unknown collection type: {collection_type}")
        
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="file_path",
                            match=MatchValue(value=file_path)
                        )
                    ]
                )
            )
            logger.info(f"Deleted chunks for file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete chunks for {file_path}: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check if vector store is healthy"""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            return False