"""
Embedders Module
Provides multiple embedding strategies with automatic fallback
"""

from .base_embedder import BaseEmbedder
from .jina_embedder import JinaEmbedder
from .huggingface_embedder import HuggingFaceEmbedder
from .gemini_embedder import GeminiEmbedder
from .local_embedder import LocalEmbedder
from .smart_embedder import SmartEmbedder
from .cache_manager import CacheManager

__all__ = [
    'BaseEmbedder',
    'JinaEmbedder',
    'HuggingFaceEmbedder',
    'GeminiEmbedder',
    'LocalEmbedder',
    'SmartEmbedder',
    'CacheManager'
]