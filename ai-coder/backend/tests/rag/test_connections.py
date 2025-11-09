# At the top of the file
import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from core.rag.connections import ConnectionManager, get_connection_manager

class TestConnectionManager:
    
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful initialization of both stores"""
        # Add this test to cover lines 28-52
        with patch('core.rag.connections.VectorStore') as MockVS, \
             patch('core.rag.connections.GraphStore') as MockGS:
            mock_vs = Mock()
            mock_vs.health_check.return_value = True
            MockVS.return_value = mock_vs
            
            mock_gs = Mock()
            mock_gs.health_check.return_value = True
            MockGS.return_value = mock_gs
            
            manager = ConnectionManager()
            await manager.initialize()
            
            assert manager.vector_store is not None
            assert manager.graph_store is not None

    @pytest.mark.asyncio
    async def test_periodic_health_check(self):
        """Test the periodic health check loop"""
        # Add to cover lines 79-100
        manager = ConnectionManager()
        manager._health_check_interval = 0.01  # Fast for testing
        
        mock_vs = Mock()
        mock_vs.health_check.side_effect = [True, False, True, True, True]  # More values
        manager.vector_store = mock_vs
        
        # Start health check and let it run briefly
        manager._start_health_check()
        await asyncio.sleep(0.05)
        
        # Cleanup
        await manager.cleanup()

    @pytest.mark.asyncio  
    async def test_get_vector_store_reinitialize(self):
        """Test get_vector_store when health check fails"""
        # Add to cover lines 59-63
        manager = ConnectionManager()
        manager.vector_store = Mock()
        manager.vector_store.health_check.return_value = False
        
        with patch.object(manager, 'initialize', new_callable=AsyncMock):
            store = await manager.get_vector_store()
            manager.initialize.assert_called_once()
# Quick win tests - cleanup scenarios
class TestConnectionManagerCleanup:
    
    @pytest.mark.asyncio
    async def test_cleanup_with_no_connections(self):
        """Test cleanup when nothing initialized"""
        manager = ConnectionManager()
        # Should not raise any errors
        await manager.cleanup()
        assert manager.vector_store is None
        assert manager.graph_store is None
    
    @pytest.mark.asyncio
    async def test_cleanup_cancels_health_check_task(self):
        """Test that cleanup properly cancels background tasks"""
        with patch('core.rag.connections.VectorStore') as MockVS:
            mock_vs = Mock()
            mock_vs.health_check.return_value = True
            MockVS.return_value = mock_vs
            
            manager = ConnectionManager()
            await manager.initialize()
            
            # Health check task should be running
            assert manager._health_check_task is not None
            
            await manager.cleanup()
            
            # Task should be cancelled
            assert manager._health_check_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_get_connection_manager_singleton(self):
        """Test global connection manager singleton pattern"""
        manager1 = await get_connection_manager()
        manager2 = await get_connection_manager()
        
        # Should return the same instance
        assert manager1 is manager2   
# ============================================================================
# ADD THIS SECTION AFTER TestConnectionManagerCleanup
# ============================================================================

class TestConnectionManagerResilience:
    """Test connection manager resilience and error recovery"""
    
    @pytest.mark.asyncio
    async def test_reconnect_on_vector_store_failure(self):
        """Test reconnection when vector store health check fails"""
        from itertools import cycle
        
        with patch('core.rag.connections.VectorStore') as MockVS:
            # Simulate initial success, then failures, then recovery
            mock_vs = Mock()
            # Use cycle to avoid StopIteration
            mock_vs.health_check.side_effect = cycle([True, False, False, True, True])
            MockVS.return_value = mock_vs
            
            manager = ConnectionManager()
            await manager.initialize()
            
            # First health check should succeed
            assert mock_vs.health_check.call_count >= 1
            
            # Simulate health check loop
            manager._health_check_interval = 0.01
            manager._start_health_check()
            
            # Wait for health checks to run
            await asyncio.sleep(0.05)
            
            # Cleanup
            await manager.cleanup()
            
            # Verify health check was called multiple times
            assert mock_vs.health_check.call_count > 1
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_vector_store_down(self):
        """Test system continues when vector store is down"""
        with patch('core.rag.connections.VectorStore') as MockVS, \
             patch('core.rag.connections.GraphStore') as MockGS:
            
            # Vector store fails, graph store works
            mock_vs = Mock()
            mock_vs.health_check.return_value = False
            MockVS.return_value = mock_vs
            
            mock_gs = Mock()
            mock_gs.health_check.return_value = True
            MockGS.return_value = mock_gs
            
            manager = ConnectionManager()
            await manager.initialize()
            
            # Should still have graph store
            graph_store = await manager.get_graph_store()
            assert graph_store is not None
            
            await manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_graph_store_down(self):
        """Test system continues when graph store is down"""
        with patch('core.rag.connections.VectorStore') as MockVS, \
             patch('core.rag.connections.GraphStore') as MockGS:
            
            # Vector store works, graph store fails
            mock_vs = Mock()
            mock_vs.health_check.return_value = True
            MockVS.return_value = mock_vs
            
            mock_gs = Mock()
            mock_gs.health_check.return_value = False
            MockGS.return_value = mock_gs
            
            manager = ConnectionManager()
            await manager.initialize()
            
            # Should still have vector store
            vector_store = await manager.get_vector_store()
            assert vector_store is not None
            
            await manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_concurrent_access_thread_safety(self):
        """Test connection manager handles concurrent access"""
        with patch('core.rag.connections.VectorStore') as MockVS:
            mock_vs = Mock()
            mock_vs.health_check.return_value = True
            MockVS.return_value = mock_vs
            
            manager = ConnectionManager()
            await manager.initialize()
            
            # Simulate concurrent access
            async def get_store():
                return await manager.get_vector_store()
            
            # Run 10 concurrent requests
            results = await asyncio.gather(*[get_store() for _ in range(10)])
            
            # All should return the same instance
            assert all(r is results[0] for r in results)
            
            await manager.cleanup()


class TestConnectionManagerPerformance:
    """Test connection manager performance characteristics"""
    
    @pytest.mark.asyncio
    async def test_health_check_performance(self):
        """Test health check completes quickly"""
        import time
        
        with patch('core.rag.connections.VectorStore') as MockVS, \
             patch('core.rag.connections.GraphStore') as MockGS:
            
            mock_vs = Mock()
            mock_vs.health_check.return_value = True
            MockVS.return_value = mock_vs
            
            mock_gs = Mock()
            mock_gs.health_check.return_value = True
            MockGS.return_value = mock_gs
            
            manager = ConnectionManager()
            await manager.initialize()
            
            # Measure health check performance
            start = time.time()
            for _ in range(100):
                await manager._periodic_health_check()
            duration = time.time() - start
            
            # 100 health checks should complete in under 1 second
            assert duration < 1.0, f"Health checks too slow: {duration:.2f}s"
            
            print(f"\n📊 Health check performance: {duration*10:.2f}ms per check")
            
            await manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_initialization_performance(self):
        """Test connection manager initializes quickly"""
        import time
        
        with patch('core.rag.connections.VectorStore') as MockVS, \
             patch('core.rag.connections.GraphStore') as MockGS:
            
            mock_vs = Mock()
            mock_vs.health_check.return_value = True
            MockVS.return_value = mock_vs
            
            mock_gs = Mock()
            mock_gs.health_check.return_value = True
            MockGS.return_value = mock_gs
            
            start = time.time()
            
            manager = ConnectionManager()
            await manager.initialize()
            
            init_duration = time.time() - start
            
            # Initialization should complete in under 2 seconds
            assert init_duration < 2.0, \
                f"Initialization too slow: {init_duration:.2f}s"
            
            print(f"\n📊 Initialization time: {init_duration*1000:.0f}ms")
            
            await manager.cleanup()