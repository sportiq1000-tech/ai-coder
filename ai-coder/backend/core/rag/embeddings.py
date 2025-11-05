"""
Code Embedding Pipeline
Handles conversion of code chunks to vector representations
"""

from typing import List, Dict, Any, Optional
import openai
import tiktoken
from utils.logger import logger
from utils.config import get_settings
from schemas.rag_schemas import CodeChunk

class CodeEmbedder:
    """
    Generates embeddings for code chunks using OpenAI's embedding models
    """
    
    def __init__(self):
        """Initialize the embedder with OpenAI client"""
        self.settings = get_settings()
        openai_api_key = getattr(self.settings, 'openai_api_key', None)
        
        if not openai_api_key:
            logger.warning("OpenAI API key not configured, embeddings will not be available")
            self.client = None
            self.model = None
            self.encoding = None
            return
            
        self.client = openai.OpenAI(api_key=openai_api_key)
        self.model = getattr(self.settings, 'embedding_model', 'text-embedding-ada-002')
        
        try:
            self.encoding = tiktoken.encoding_for_model(self.model)
        except Exception as e:
            logger.warning(f"Failed to load encoding for {self.model}, using cl100k_base: {e}")
            self.encoding = tiktoken.get_encoding("cl100k_base")
            
        self.max_tokens = 8191  # OpenAI's limit for embeddings
    
    async def embed_chunks(self, chunks: List[CodeChunk]) -> List[CodeChunk]:
        """
        Generate embeddings for a list of code chunks
        
        Args:
            chunks: List of code chunks to embed
            
        Returns:
            List of code chunks with embeddings added
        """
        if not self.client:
            logger.warning("OpenAI client not available, skipping embedding generation")
            return chunks
            
        if not chunks:
            return chunks
        
        # Prepare texts for embedding
        texts = []
        for chunk in chunks:
            text = self._prepare_text_for_embedding(chunk)
            texts.append(text)
        
        # Generate embeddings in batches
        batch_size = getattr(self.settings, 'embedding_batch_size', 100)
        all_embeddings = []
        embedding_dim = getattr(self.settings, 'embedding_dimension', 1536)
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch_texts
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
                logger.info(f"Generated embeddings for batch {i//batch_size + 1}")
                
            except Exception as e:
                logger.error(f"Failed to generate embeddings for batch {i//batch_size + 1}: {e}")
                # Add zero embeddings for failed batch
                all_embeddings.extend([[0.0] * embedding_dim] * len(batch_texts))
        
        # Add embeddings to chunks
        for i, chunk in enumerate(chunks):
            if i < len(all_embeddings):
                chunk.embedding = all_embeddings[i]
        
        return chunks
    
    def _prepare_text_for_embedding(self, chunk: CodeChunk) -> str:
        """
        Prepare code chunk text for embedding
        
        Args:
            chunk: Code chunk to prepare
            
        Returns:
            Prepared text for embedding
        """
        # Create a rich text representation
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
        
        # Combine and truncate if necessary
        text = "\n".join(parts)
        
        # Truncate to max tokens
        if self.encoding:
            tokens = self.encoding.encode(text)
            if len(tokens) > self.max_tokens:
                tokens = tokens[:self.max_tokens]
                text = self.encoding.decode(tokens)
        
        return text
    
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query
        
        Args:
            query: Search query string
            
        Returns:
            Query embedding vector
        """
        if not self.client:
            logger.warning("OpenAI client not available")
            embedding_dim = getattr(self.settings, 'embedding_dimension', 1536)
            return [0.0] * embedding_dim
            
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=query
            )
            
            embedding = response.data[0].embedding
            logger.info(f"Generated query embedding with {len(embedding)} dimensions")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        if not self.encoding:
            return len(text) // 4  # Rough estimate
        return len(self.encoding.encode(text))