"""
Verifies that sample data exists in RAG databases.
Exits with code 1 if data is missing.
"""
import asyncio
import sys
import os
from pathlib import Path

# Setup Python path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

# Change to backend directory for .env loading
original_dir = os.getcwd()
os.chdir(backend_path)

try:
    from core.rag.connections import get_connection_manager
    from utils.logger import logger
    from qdrant_client import QdrantClient
    from utils.config import get_settings
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)


async def main():
    """Check if sample data exists in databases"""
    logger.info("=" * 60)
    logger.info("🔎 Verifying RAG Sample Data...")
    logger.info("=" * 60)
    
    manager = None
    all_ok = True
    
    try:
        settings = get_settings()
        manager = await get_connection_manager()
        
        # --- Check Vector Store ---
        logger.info("\n📊 VECTOR STORE (Qdrant)")
        vector_store = await manager.get_vector_store()
        
        # ✅ FIX: Pass API key directly
        if vector_store and vector_store.health_check():
            logger.info("✅ Qdrant is healthy")
            
            try:
                # Initialize client with API key
                qdrant = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY
                )
                
                count_result = qdrant.count(collection_name="code_chunks", exact=True)
                points_count = count_result.count
                
                logger.info(f"   Vector points in 'code_chunks': {points_count}")
                if points_count > 0:
                    logger.info("   ✅ Embeddings are loaded.")
                else:
                    logger.warning("   ⚠️  No embeddings found in 'code_chunks' collection.")
                    all_ok = False
            except Exception as e:
                logger.error(f"   ❌ Failed to query Qdrant: {e}")
                all_ok = False
        else:
            logger.error("❌ Qdrant is not healthy.")
            all_ok = False
            
        # --- Check Graph Store ---
        logger.info("\n📊 GRAPH STORE (Neo4j)")
        graph_store = await manager.get_graph_store()
        if graph_store and graph_store.health_check():
            logger.info("✅ Neo4j is healthy")
            try:
                with graph_store.driver.session(database=settings.NEO4J_DATABASE) as session:
                    result = session.run("MATCH (n) RETURN count(n) as count")
                    node_count = result.single()["count"]
                    logger.info(f"   Total nodes: {node_count}")
                    if node_count > 0:
                        logger.info("   ✅ Graph structure is loaded.")
                    else:
                        logger.warning("   ⚠️  No nodes found in graph database.")
                        all_ok = False
            except Exception as e:
                logger.error(f"   ❌ Failed to query Neo4j: {e}")
                all_ok = False
        else:
            logger.error("❌ Neo4j is not healthy.")
            all_ok = False

    except Exception as e:
        logger.error(f"Error during verification: {e}")
        all_ok = False
    finally:
        if manager:
            await manager.cleanup()

    # --- Final Verdict ---
    logger.info("\n" + "=" * 60)
    if all_ok:
        logger.info("🎉 SUCCESS: RAG data verification passed!")
        sys.exit(0)
    else:
        logger.error("❌ FAILED: RAG data verification failed.")
        logger.warning("💡 Run 'python scripts/load_sample_with_embeddings.py' to load data if needed.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)
    finally:
        os.chdir(original_dir)