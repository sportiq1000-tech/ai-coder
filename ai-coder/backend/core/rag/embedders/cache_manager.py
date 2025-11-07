"""
Cache Manager for Embeddings
Handles persistent caching with compression and TTL
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import msgpack
from datetime import datetime, timedelta
from utils.logger import logger


class CacheManager:
    """
    Manages embedding cache with compression and automatic cleanup
    """
    
    def __init__(self, 
                 cache_dir: str,
                 compression: bool = True,
                 ttl_days: int = 30,
                 max_size_gb: float = 1.0):
        """
        Initialize cache manager
        
        Args:
            cache_dir: Directory for cache storage
            compression: Use msgpack compression
            ttl_days: Time-to-live in days
            max_size_gb: Maximum cache size in GB
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.compression = compression
        self.ttl_seconds = ttl_days * 24 * 3600
        self.max_size_bytes = max_size_gb * 1024 * 1024 * 1024
        
        # Metadata file
        self.metadata_file = self.cache_dir / "metadata.json"
        self.metadata = self._load_metadata()
        
        # Cleanup old entries on init
        self._cleanup_old_entries()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")
        
        return {
            "created_at": datetime.now().isoformat(),
            "total_entries": 0,
            "total_size_bytes": 0,
            "last_cleanup": datetime.now().isoformat()
        }
    
    def _save_metadata(self):
        """Save cache metadata"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")
    
    def _get_cache_key(self, text: str, model: str) -> str:
        """
        Generate cache key for text and model
        
        Args:
            text: Text to hash
            model: Model name
            
        Returns:
            Cache key (hex string)
        """
        # Create deterministic hash
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get file path for cache key"""
        # Use first 2 chars for subdirectory (better filesystem performance)
        subdir = self.cache_dir / cache_key[:2]
        subdir.mkdir(exist_ok=True)
        
        extension = ".msgpack" if self.compression else ".json"
        return subdir / f"{cache_key}{extension}"
    
    def get(self, text: str, model: str) -> Optional[List[float]]:
        """
        Get embedding from cache
        
        Args:
            text: Text to lookup
            model: Model name
            
        Returns:
            Cached embedding or None
        """
        cache_key = self._get_cache_key(text, model)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            # Check TTL
            mtime = cache_path.stat().st_mtime
            age = time.time() - mtime
            
            if age > self.ttl_seconds:
                # Expired, delete
                cache_path.unlink()
                return None
            
            # Load from cache
            if self.compression:
                with open(cache_path, 'rb') as f:
                    data = msgpack.unpackb(f.read(), raw=False)
            else:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
            
            return data.get("embedding")
            
        except Exception as e:
            logger.warning(f"Failed to read from cache: {e}")
            # Delete corrupted cache file
            try:
                cache_path.unlink()
            except:
                pass
            return None
    
    def set(self, text: str, model: str, embedding: List[float]):
        """
        Store embedding in cache
        
        Args:
            text: Text that was embedded
            model: Model name
            embedding: Embedding vector
        """
        cache_key = self._get_cache_key(text, model)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            data = {
                "text_hash": cache_key,
                "model": model,
                "embedding": embedding,
                "cached_at": datetime.now().isoformat(),
                "dimension": len(embedding)
            }
            
            # Write to cache
            if self.compression:
                with open(cache_path, 'wb') as f:
                    f.write(msgpack.packb(data, use_bin_type=True))
            else:
                with open(cache_path, 'w') as f:
                    json.dump(data, f)
            
            # Update metadata
            self.metadata["total_entries"] += 1
            self.metadata["total_size_bytes"] = self._calculate_cache_size()
            
            # FIX: Save the metadata after updating it.
            self._save_metadata()
            
            # Check if cleanup needed
            if self.metadata["total_size_bytes"] > self.max_size_bytes:
                self._cleanup_by_size()
            
        except Exception as e:
            logger.error(f"Failed to write to cache: {e}")
    
    def get_batch(self, texts: List[str], model: str) -> List[Optional[List[float]]]:
        """
        Get multiple embeddings from cache
        
        Args:
            texts: List of texts
            model: Model name
            
        Returns:
            List of embeddings (None for cache misses)
        """
        return [self.get(text, model) for text in texts]
    
    def set_batch(self, texts: List[str], model: str, embeddings: List[List[float]]):
        """
        Store multiple embeddings in cache
        
        Args:
            texts: List of texts
            model: Model name
            embeddings: List of embedding vectors
        """
        for text, embedding in zip(texts, embeddings):
            if embedding is not None:
                self.set(text, model, embedding)
    
    def _calculate_cache_size(self) -> int:
        """Calculate total cache size in bytes"""
        total_size = 0
        for file_path in self.cache_dir.rglob("*"):
            if file_path.is_file() and file_path.name != "metadata.json":
                total_size += file_path.stat().st_size
        return total_size
    
    def _cleanup_old_entries(self):
        """Remove entries older than TTL"""
        current_time = time.time()
        removed_count = 0
        
        for file_path in self.cache_dir.rglob("*"):
            if file_path.is_file() and file_path.name != "metadata.json":
                mtime = file_path.stat().st_mtime
                age = current_time - mtime
                
                if age > self.ttl_seconds:
                    try:
                        file_path.unlink()
                        removed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete old cache file: {e}")
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old cache entries")
            self.metadata["last_cleanup"] = datetime.now().isoformat()
            self._save_metadata()
    
    def _cleanup_by_size(self):
        """Remove oldest entries when size limit exceeded"""
        # Get all cache files with their modification times
        files = []
        for file_path in self.cache_dir.rglob("*"):
            if file_path.is_file() and file_path.name != "metadata.json":
                files.append((file_path, file_path.stat().st_mtime))
        
        # Sort by modification time (oldest first)
        files.sort(key=lambda x: x[1])
        
        # Remove oldest 20% of files
        remove_count = len(files) // 5
        removed = 0
        
        for file_path, _ in files[:remove_count]:
            try:
                file_path.unlink()
                removed += 1
            except Exception as e:
                logger.warning(f"Failed to delete cache file during cleanup: {e}")
        
        logger.info(f"Size-based cleanup: removed {removed} cache entries")
        self.metadata["total_size_bytes"] = self._calculate_cache_size()
        self.metadata["last_cleanup"] = datetime.now().isoformat()
        self._save_metadata()
    
    def clear(self):
        """Clear all cache entries"""
        removed_count = 0
        for file_path in self.cache_dir.rglob("*"):
            if file_path.is_file() and file_path.name != "metadata.json":
                try:
                    file_path.unlink()
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete cache file: {e}")
        
        self.metadata["total_entries"] = 0
        self.metadata["total_size_bytes"] = 0
        self._save_metadata()
        
        logger.info(f"Cleared {removed_count} cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_dir": str(self.cache_dir),
            "total_entries": self.metadata.get("total_entries", 0),
            "total_size_mb": self.metadata.get("total_size_bytes", 0) / (1024 * 1024),
            "max_size_gb": self.max_size_bytes / (1024 * 1024 * 1024),
            "compression_enabled": self.compression,
            "ttl_days": self.ttl_seconds / (24 * 3600),
            "last_cleanup": self.metadata.get("last_cleanup"),
            "created_at": self.metadata.get("created_at")
        }