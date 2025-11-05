"""
RAG Configuration Management
Re-exports settings from main config for backward compatibility
"""

from utils.config import settings, get_settings, Settings

# For backward compatibility, create aliases
RAGSettings = Settings  # Alias the main Settings class
get_rag_settings = get_settings  # Alias the getter function

# Export everything
__all__ = ['settings', 'get_settings', 'get_rag_settings', 'Settings', 'RAGSettings']