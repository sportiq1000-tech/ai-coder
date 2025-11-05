"""
Database Connection Management
Manages connections to Qdrant and Neo4j with proper error handling
"""

import asyncio
from typing import Optional
from utils.logger import logger
from .config import get_rag_settings
from .vector_store import VectorStore
from .graph_store import GraphStore

class ConnectionManager:
    """
    Manages database connections with health checks and reconnection logic
    """
    
    def __init__(self):
        """Initialize connection manager"""
        self.settings = get_rag_settings()
        self.vector_store: Optional[VectorStore] = None
        self.graph_store: Optional[GraphStore] = None
        self._connection_lock = asyncio.Lock()
        self._health_check_interval = 60  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize all database connections"""
        async with self._connection_lock:
            try:
                # Initialize vector store
                logger.info("Initializing vector store...")
                self.vector_store = VectorStore()
                if not self.vector_store.health_check():
                    logger.warning("Vector store health check failed")
                else:
                    logger.info("Vector store initialized successfully")
                
                # Initialize graph store
                logger.info("Initializing graph store...")
                try:
                    self.graph_store = GraphStore()
                    if not self.graph_store.health_check():
                        logger.warning("Graph store health check failed")
                    else:
                        logger.info("Graph store initialized successfully")
                except Exception as e:
                    logger.warning(f"Graph store initialization failed: {e}")
                    self.graph_store = None
                
                # Start health check task
                self._start_health_check()
                
                logger.info("RAG database connections initialized")
                
            except Exception as e:
                logger.error(f"Failed to initialize RAG connections: {e}")
                # Don't raise - allow application to run with degraded functionality
    
    async def get_vector_store(self) -> VectorStore:
        """Get vector store instance, ensuring it's connected"""
        if not self.vector_store or not self.vector_store.health_check():
            await self.initialize()
        return self.vector_store
    
    async def get_graph_store(self) -> Optional[GraphStore]:
        """Get graph store instance, ensuring it's connected"""
        if not self.graph_store or not self.graph_store.health_check():
            await self.initialize()
        return self.graph_store
    
    def _start_health_check(self):
        """Start periodic health check task"""
        if self._health_check_task:
            self._health_check_task.cancel()
        
        self._health_check_task = asyncio.create_task(self._periodic_health_check())
    
    async def _periodic_health_check(self):
        """Periodically check connection health"""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                # Check vector store
                if self.vector_store and not self.vector_store.health_check():
                    logger.warning("Vector store health check failed, attempting reconnection")
                    try:
                        self.vector_store = VectorStore()
                    except Exception as e:
                        logger.error(f"Failed to reconnect vector store: {e}")
                
                # Check graph store
                if self.graph_store and not self.graph_store.health_check():
                    logger.warning("Graph store health check failed, attempting reconnection")
                    try:
                        self.graph_store = GraphStore()
                    except Exception as e:
                        logger.error(f"Failed to reconnect graph store: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def cleanup(self):
        """Cleanup connections and tasks"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self.graph_store:
            self.graph_store.close()
            self.graph_store = None
        
        self.vector_store = None
        logger.info("RAG connections cleaned up")

# Global connection manager instance
_connection_manager: Optional[ConnectionManager] = None

async def get_connection_manager() -> ConnectionManager:
    """Get global connection manager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
        await _connection_manager.initialize()
    return _connection_manager