"""
Smart Embedder Orchestrator
Manages multiple embedders with automatic fallback
"""

from typing import List, Optional, Dict, Any
from utils.logger import logger
from utils.config import get_settings
from schemas.rag_schemas import CodeChunk
from .base_embedder import BaseEmbedder
from .jina_embedder import JinaEmbedder
from .huggingface_embedder import HuggingFaceEmbedder
from .gemini_embedder import GeminiEmbedder
from .local_embedder import LocalEmbedder


class SmartEmbedder:
    """
    Intelligent embedder with automatic fallback chain
    
    Fallback priority:
    1. Jina AI (primary - free, no API key)
    2. HuggingFace (fallback 1 - requires API key)
    3. Gemini (fallback 2 - requires API key)
    4. Local (fallback 3 - always works, offline)
    """
    
    def __init__(self):
        """Initialize smart embedder with all fallbacks"""
        self.settings = get_settings()
        
        # Initialize all embedders
        self.primary = None
        self.fallbacks = []
        
        self._initialize_embedders()
        
        # Statistics
        self.total_requests = 0
        self.embedder_usage = {
            "jina": 0,
            "huggingface": 0,
            "gemini": 0,
            "local": 0
        }
        
        logger.info(f"SmartEmbedder initialized with {len(self.fallbacks)} fallbacks")
    
    def _initialize_embedders(self):
        """Initialize all available embedders"""
        all_embedders = []
        
        # Try to initialize all potential embedders
        try:
            all_embedders.append(JinaEmbedder())
        except Exception as e:
            logger.error(f"Failed to initialize Jina embedder: {e}")
            
        try:
            hf_embedder = HuggingFaceEmbedder()
            if hf_embedder.api_key:
                all_embedders.append(hf_embedder)
            else:
                logger.info("ℹ️  HuggingFace: No API key configured (skipped)")
        except Exception as e:
            logger.warning(f"Failed to initialize HuggingFace embedder: {e}")
            
        try:
            gemini_embedder = GeminiEmbedder()
            if gemini_embedder.api_key:
                all_embedders.append(gemini_embedder)
            else:
                logger.info("ℹ️  Gemini: No API key configured (skipped)")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini embedder: {e}")
            
        try:
            all_embedders.append(LocalEmbedder())
        except Exception as e:
            logger.warning(f"Failed to initialize Local embedder: {e}")
            
        # FIX: Correctly assign primary and fallbacks based on health checks
        healthy_embedders = []
        for embedder in all_embedders:
            if embedder.health_check():
                healthy_embedders.append(embedder)
                logger.info(f"✅ {embedder.__class__.__name__} is healthy and available.")
            else:
                logger.warning(f"⚠️  {embedder.__class__.__name__} health check failed.")

        if healthy_embedders:
            self.primary = healthy_embedders[0]
            self.fallbacks = healthy_embedders[1:]
            logger.info(f"Promoted {self.primary.__class__.__name__} to primary.")
            if self.fallbacks:
                logger.info(f"Available fallbacks: {[e.__class__.__name__ for e in self.fallbacks]}")
        else:
            logger.error("❌ No healthy embedders available! Please check your configuration and network.")
    
    async def embed_chunks(self, chunks: List[CodeChunk]) -> List[CodeChunk]:
        """
        Generate embeddings for code chunks with automatic fallback
        
        Args:
            chunks: List of code chunks to embed
            
        Returns:
            List of code chunks with embeddings added
        """
        if not chunks:
            return chunks
        
        self.total_requests += 1
        
        # Prepare texts for embedding
        texts = []
        for chunk in chunks:
            text = self._prepare_text_for_embedding(chunk)
            texts.append(text)
        
        # Try primary embedder first
        embeddings = None
        embedder_used = None
        
        if self.primary:
            try:
                logger.info(f"Trying primary embedder: {self.primary.__class__.__name__}")
                embeddings = await self.primary.embed_batch(texts)
                
                # Check if all embeddings succeeded
                if embeddings and all(emb is not None for emb in embeddings):
                    embedder_used = self.primary.__class__.__name__.lower().replace('embedder', '')
                    self.embedder_usage[embedder_used] = self.embedder_usage.get(embedder_used, 0) + 1
                    logger.info(f"✅ Successfully embedded {len(embeddings)} chunks with {embedder_used}")
                else:
                    logger.warning(f"Primary embedder returned incomplete results")
                    embeddings = None
                    
            except Exception as e:
                logger.error(f"Primary embedder failed: {e}")
                embeddings = None
        
        # Try fallbacks if primary failed
        if embeddings is None and self.fallbacks:
            for i, fallback_embedder in enumerate(self.fallbacks):
                try:
                    logger.info(f"Trying fallback {i+1}: {fallback_embedder.__class__.__name__}")
                    embeddings = await fallback_embedder.embed_batch(texts)
                    
                    if embeddings and all(emb is not None for emb in embeddings):
                        embedder_used = fallback_embedder.__class__.__name__.lower().replace('embedder', '')
                        self.embedder_usage[embedder_used] = self.embedder_usage.get(embedder_used, 0) + 1
                        logger.info(f"✅ Fallback {i+1} succeeded: {embedder_used}")
                        break
                    else:
                        logger.warning(f"Fallback {i+1} returned incomplete results")
                        embeddings = None
                        
                except Exception as e:
                    logger.error(f"Fallback {i+1} failed: {e}")
                    embeddings = None
                    continue
        
        # If all embedders failed, return chunks without embeddings
        if embeddings is None:
            logger.error("❌ All embedders failed! Returning chunks without embeddings")
            return chunks
        
        # Add embeddings to chunks
        for i, chunk in enumerate(chunks):
            if i < len(embeddings) and embeddings[i] is not None:
                chunk.embedding = embeddings[i]
        
        return chunks
    
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query
        
        Args:
            query: Search query string
            
        Returns:
            Query embedding vector
        """
        # Try primary first
        if self.primary:
            try:
                embedding = await self.primary.embed_single(query)
                if embedding is not None:
                    return embedding
            except Exception as e:
                logger.error(f"Primary embedder failed for query: {e}")
        
        # Try fallbacks
        for fallback_embedder in self.fallbacks:
            try:
                embedding = await fallback_embedder.embed_single(query)
                if embedding is not None:
                    return embedding
            except Exception as e:
                logger.error(f"Fallback embedder failed for query: {e}")
                continue
        
        # If all failed, return zero vector
        logger.error("All embedders failed for query, returning zero vector")
        dimension = getattr(self.settings, 'EMBEDDING_DIMENSION', 768)
        return [0.0] * dimension
    
    def _prepare_text_for_embedding(self, chunk: CodeChunk) -> str:
        """
        Prepare code chunk text for embedding
        
        Args:
            chunk: Code chunk to prepare
            
        Returns:
            Prepared text for embedding
        """
        parts = []
        
        # Add context information
        if chunk.file_path:
            parts.append(f"File: {chunk.file_path}")
        
        if chunk.language:
            parts.append(f"Language: {chunk.language}")
        
        if chunk.chunk_type:
            parts.append(f"Type: {chunk.chunk_type}")
        
        # Add function/class signature if available
        if chunk.metadata.get("signature"):
            parts.append(f"Signature: {chunk.metadata['signature']}")
        
        # Add the actual code
        parts.append("Code:")
        parts.append(chunk.content)
        
        # Add additional metadata
        if chunk.metadata.get("docstring"):
            parts.append(f"Documentation: {chunk.metadata['docstring']}")
        
        if chunk.metadata.get("complexity"):
            parts.append(f"Complexity: {chunk.metadata['complexity']}")
        
        return "\n".join(parts)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics
        
        Returns:
            Statistics dictionary
        """
        stats = {
            "total_requests": self.total_requests,
            "embedder_usage": self.embedder_usage,
            "primary_embedder": self.primary.__class__.__name__ if self.primary else None,
            "fallback_count": len(self.fallbacks),
            "fallbacks_available": [fb.__class__.__name__ for fb in self.fallbacks]
        }
        
        # Add primary embedder stats
        if self.primary:
            stats["primary_stats"] = self.primary.get_stats()
            
            # Add token usage if Jina
            if isinstance(self.primary, JinaEmbedder):
                stats["token_usage"] = self.primary.get_token_usage()
        
        # Add fallback stats
        stats["fallback_stats"] = [
            fb.get_stats() for fb in self.fallbacks
        ]
        
        return stats
    
    def health_check(self) -> Dict[str, bool]:
        """
        Check health of all embedders
        
        Returns:
            Health status for each embedder
        """
        health = {}
        
        if self.primary:
            primary_name = self.primary.__class__.__name__
            health[primary_name] = self.primary.health_check()
        
        for fallback in self.fallbacks:
            fallback_name = fallback.__class__.__name__
            health[fallback_name] = fallback.health_check()
        
        return health