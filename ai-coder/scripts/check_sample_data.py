"""
Check if sample data is loaded in RAG databases
"""

import asyncio
import sys
import os
from pathlib import Path

# Fix: Determine paths correctly from scripts/ directory
script_dir = Path(__file__).resolve().parent  # /workspaces/ai-coder/ai-coder/scripts
project_root = script_dir.parent               # /workspaces/ai-coder/ai-coder
backend_path = project_root / "backend"        # /workspaces/ai-coder/ai-coder/backend

# Add backend to Python path
sys.path.insert(0, str(backend_path))

# Change to backend directory for .env loading
original_dir = os.getcwd()
os.chdir(backend_path)

try:
    from core.rag.connections import get_connection_manager
    from utils.logger import logger

    async def check_sample_data():
        """Check if sample data exists in databases"""
        
        logger.info("=" * 60)
        logger.info("Checking RAG Sample Data...")
        logger.info("=" * 60)
        
        try:
            # Get connection manager
            conn_manager = await get_connection_manager()
            
            # Check Vector Store
            logger.info("\n📊 VECTOR STORE (Qdrant)")
            logger.info("-" * 60)
            vector_store = await conn_manager.get_vector_store()
            
            if vector_store.health_check():
                logger.info("✅ Qdrant is healthy")
                
                # Try to get collection info
                try:
                    collections = vector_store.client.get_collections()
                    logger.info(f"Collections found: {len(collections.collections)}")
                    
                    total_points = 0
                    for collection in collections.collections:
                        info = vector_store.client.get_collection(collection.name)
                        logger.info(f"  - {collection.name}: {info.points_count} points")
                        total_points += info.points_count
                        
                        if info.points_count == 0:
                            logger.warning(f"    ⚠️  No data in {collection.name} (need OpenAI key for embeddings)")
                        else:
                            logger.info(f"    ✅ Contains sample data")
                    
                    if total_points == 0:
                        logger.warning("\n⚠️  No embeddings stored - OpenAI API key needed for vector data")
                        logger.info("💡 To enable embeddings:")
                        logger.info("   1. Get API key from https://platform.openai.com/api-keys")
                        logger.info("   2. Add to backend/.env: OPENAI_API_KEY=sk-proj-...")
                        logger.info("   3. Re-run: python scripts/setup_rag_databases.py")
                        
                except Exception as e:
                    logger.error(f"Failed to get collection info: {e}")
            else:
                logger.error("❌ Qdrant is not healthy")
            
            # Check Graph Store
            logger.info("\n📊 GRAPH STORE (Neo4j)")
            logger.info("-" * 60)
            graph_store = await conn_manager.get_graph_store()
            
            if graph_store and graph_store.health_check():
                logger.info("✅ Neo4j is healthy")
                
                # Count nodes
                try:
                    from utils.config import get_settings
                    settings = get_settings()
                    neo4j_database = getattr(settings, 'NEO4J_DATABASE', 'neo4j')
                    
                    with graph_store.driver.session(database=neo4j_database) as session:
                        # Count all nodes
                        result = session.run("MATCH (n) RETURN count(n) as count")
                        node_count = result.single()["count"]
                        logger.info(f"Total nodes: {node_count}")
                        
                        if node_count == 0:
                            logger.warning("  ⚠️  No nodes found - sample data not loaded")
                        else:
                            logger.info("  ✅ Contains sample data")
                            
                            # Count by type
                            result = session.run("""
                                MATCH (n) 
                                RETURN labels(n)[0] as type, count(n) as count
                                ORDER BY type
                            """)
                            logger.info("\n  📋 Node breakdown:")
                            for record in result:
                                logger.info(f"    - {record['type']}: {record['count']}")
                            
                            # Count relationships
                            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                            rel_count = result.single()["count"]
                            logger.info(f"\n  🔗 Total relationships: {rel_count}")
                            
                            # Breakdown relationships
                            result = session.run("""
                                MATCH ()-[r]->()
                                RETURN type(r) as type, count(r) as count
                                ORDER BY type
                            """)
                            logger.info("\n  📋 Relationship breakdown:")
                            for record in result:
                                logger.info(f"    - {record['type']}: {record['count']}")
                            
                            # Sample nodes
                            logger.info("\n  📄 Sample nodes:")
                            result = session.run("""
                                MATCH (n)
                                RETURN labels(n)[0] as type, 
                                       coalesce(n.name, n.path) as identifier
                                LIMIT 5
                            """)
                            for record in result:
                                node_type = record['type']
                                identifier = record['identifier']
                                logger.info(f"    - {node_type}: {identifier}")
                            
                except Exception as e:
                    logger.error(f"Failed to query Neo4j: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.warning("⚠️  Neo4j is not available or not healthy")
            
            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("📊 SUMMARY")
            logger.info("=" * 60)
            
            has_vector_data = False
            has_graph_data = False
            
            try:
                collections = vector_store.client.get_collections()
                for collection in collections.collections:
                    info = vector_store.client.get_collection(collection.name)
                    if info.points_count > 0:
                        has_vector_data = True
                        break
            except:
                pass
            
            try:
                if graph_store:
                    with graph_store.driver.session(database=neo4j_database) as session:
                        result = session.run("MATCH (n) RETURN count(n) as count")
                        if result.single()["count"] > 0:
                            has_graph_data = True
            except:
                pass
            
            if has_vector_data:
                logger.info("✅ Vector data loaded (embeddings available)")
            else:
                logger.warning("⚠️  No vector data (need OpenAI key for embeddings)")
            
            if has_graph_data:
                logger.info("✅ Graph data loaded (code structure available)")
            else:
                logger.warning("⚠️  No graph data loaded")
            
            logger.info("\n💡 Quick Access:")
            logger.info("   • Qdrant Dashboard: http://localhost:6333/dashboard")
            logger.info("   • Neo4j Query: docker exec -it ai-coder-neo4j cypher-shell -u neo4j -p password123")
            
            logger.info("=" * 60)
            
            # Cleanup
            await conn_manager.cleanup()
            
        except Exception as e:
            logger.error(f"Error checking sample data: {e}")
            import traceback
            logger.error(traceback.format_exc())


    if __name__ == "__main__":
        try:
            asyncio.run(check_sample_data())
        except KeyboardInterrupt:
            logger.info("Check interrupted by user")
        except Exception as e:
            logger.error(f"Check failed: {e}")
            sys.exit(1)
        finally:
            # Change back to original directory
            os.chdir(original_dir)

except ImportError as e:
    print(f"❌ Import Error: {e}")
    print(f"Script directory: {script_dir}")
    print(f"Project root: {project_root}")
    print(f"Backend path: {backend_path}")
    print(f"Python path: {sys.path[:3]}")
    sys.exit(1)