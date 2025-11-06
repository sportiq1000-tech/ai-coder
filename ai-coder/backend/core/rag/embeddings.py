"""
Code Embedding Pipeline
Handles conversion of code chunks to vector representations

UPDATED: Now uses SmartEmbedder with automatic fallback chain
- Primary: Jina AI (free, no API key)
- Fallback 1: HuggingFace (requires API key)
- Fallback 2: Gemini (requires API key)
- Fallback 3: Local Sentence Transformers (always works)
"""

from typing import List, Dict, Any, Optional
from utils.logger import logger
from utils.config import get_settings
from schemas.rag_schemas import CodeChunk
from core.rag.embedders.smart_embedder import SmartEmbedder


class CodeEmbedder:
    """
    Generates embeddings for code chunks with automatic fallback
    
    This is a compatibility wrapper around SmartEmbedder that maintains
    the same API as the original OpenAI-based implementation.
    """
    
    def __init__(self):
        """Initialize the embedder with SmartEmbedder"""
        self.settings = get_settings()
        
        # Initialize SmartEmbedder (handles all providers)
        try:
            self.embedder = SmartEmbedder()
            self.client = self.embedder  # For backward compatibility
            logger.info("CodeEmbedder initialized with SmartEmbedder")
        except Exception as e:
            logger.error(f"Failed to initialize SmartEmbedder: {e}")
            self.embedder = None
            self.client = None
    
    async def embed_chunks(self, chunks: List[CodeChunk]) -> List[CodeChunk]:
        """
        Generate embeddings for a list of code chunks
        
        Args:
            chunks: List of code chunks to embed
            
        Returns:
            List of code chunks with embeddings added
        """
        if not self.embedder:
            logger.warning("SmartEmbedder not available, returning chunks without embeddings")
            return chunks
        
        if not chunks:
            return chunks
        
        try:
            # Delegate to SmartEmbedder
            return await self.embedder.embed_chunks(chunks)
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            # Return chunks without embeddings (graceful degradation)
            return chunks
    
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query
        
        Args:
            query: Search query string
            
        Returns:
            Query embedding vector
        """
        if not self.embedder:
            logger.warning("SmartEmbedder not available")
            embedding_dim = getattr(self.settings, 'EMBEDDING_DIMENSION', 768)
            return [0.0] * embedding_dim
        
        try:
            return await self.embedder.embed_query(query)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            embedding_dim = getattr(self.settings, 'EMBEDDING_DIMENSION', 768)
            return [0.0] * embedding_dim
    
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated number of tokens
        """
        # Simple word-based estimation (Jina uses ~1.3 tokens per word)
        word_count = len(text.split())
        return int(word_count * 1.3)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get embedding statistics
        
        Returns:
            Statistics dictionary
        """
        if not self.embedder:
            return {"error": "Embedder not initialized"}
        
        return self.embedder.get_stats()
    
    def health_check(self) -> Dict[str, bool]:
        """
        Check health of all embedders
        
        Returns:
            Health status
        """
        if not self.embedder:
            return {"embedder": False}
        
        return self.embedder.health_check()