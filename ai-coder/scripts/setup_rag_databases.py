"""
Script to initialize RAG databases
Run this after deploying to production
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
    from core.rag.chunker import CodeChunker
    from core.rag.embeddings import CodeEmbedder
    from schemas.rag_schemas import CodeChunk, CodeNode, CodeRelationship
    from utils.logger import logger

    async def setup_databases():
        """Setup and configure RAG databases"""
        logger.info("=" * 60)
        logger.info("Setting up RAG databases...")
        logger.info("=" * 60)
        
        try:
            # Get connection manager
            logger.info("Initializing connection manager...")
            conn_manager = await get_connection_manager()
            
            # Get stores
            logger.info("Getting vector store...")
            vector_store = await conn_manager.get_vector_store()
            
            logger.info("Getting graph store...")
            graph_store = await conn_manager.get_graph_store()
            
            # Test connections
            logger.info("Testing connections...")
            vector_healthy = vector_store.health_check()
            graph_healthy = graph_store.health_check() if graph_store else False
            
            logger.info(f"Vector Store: {'✅ Healthy' if vector_healthy else '❌ Unhealthy'}")
            logger.info(f"Graph Store: {'✅ Healthy' if graph_healthy else '❌ Unhealthy or Not Configured'}")
            
            if not vector_healthy:
                logger.warning("Vector store is not healthy, but continuing...")
            
            # Create sample data for testing
            logger.info("Creating sample data...")
            await create_sample_data(vector_store, graph_store)
            
            logger.info("=" * 60)
            logger.info("✅ Database setup completed successfully")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"❌ Database setup failed: {e}")
            logger.error("=" * 60)
            import traceback
            logger.error(traceback.format_exc())
            raise

    async def create_sample_data(vector_store, graph_store):
        """Create sample data for testing"""
        
        # Sample Python code
        sample_code = '''
def fibonacci(n):
    """Calculate nth Fibonacci number"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class MathUtils:
    """Utility class for math operations"""
    
    @staticmethod
    def factorial(n):
        """Calculate factorial of n"""
        if n <= 1:
            return 1
        return n * MathUtils.factorial(n-1)
    
    @staticmethod
    def power(base, exp):
        """Calculate power"""
        return base ** exp
'''
        
        # Process sample code
        chunker = CodeChunker()
        embedder = CodeEmbedder()
        
        logger.info("Creating chunks from sample code...")
        chunks = await chunker.chunk_file("sample.py", sample_code, "python")
        logger.info(f"Created {len(chunks)} chunks")
        
        # Generate embeddings if OpenAI is configured
        if embedder.client:
            logger.info("Generating embeddings...")
            chunks_with_embeddings = await embedder.embed_chunks(chunks)
            logger.info("Embeddings generated successfully")
        else:
            logger.warning("OpenAI not configured, skipping embeddings")
            chunks_with_embeddings = chunks
        
        # Store in vector store
        if chunks_with_embeddings and any(c.embedding for c in chunks_with_embeddings):
            logger.info("Storing chunks in vector store...")
            await vector_store.store_chunks(chunks_with_embeddings)
            logger.info("✅ Chunks stored in vector store")
        else:
            logger.warning("No chunks with embeddings to store")
        
        # Create graph nodes and relationships
        if graph_store:
            logger.info("Creating graph nodes and relationships...")
            nodes = [
                CodeNode(
                    id="sample.py",
                    type="file",
                    properties={"language": "python", "lines_of_code": 20}
                ),
                CodeNode(
                    id="fibonacci",
                    type="function",
                    properties={
                        "name": "fibonacci",
                        "signature": "fibonacci(n)",
                        "complexity": 3,
                        "start_line": 2,
                        "end_line": 6
                    }
                ),
                CodeNode(
                    id="MathUtils",
                    type="class",
                    properties={
                        "name": "MathUtils",
                        "start_line": 8,
                        "end_line": 21
                    }
                ),
                CodeNode(
                    id="factorial",
                    type="function",
                    properties={
                        "name": "factorial",
                        "signature": "factorial(n)",
                        "complexity": 2,
                        "start_line": 12,
                        "end_line": 16
                    }
                ),
                CodeNode(
                    id="power",
                    type="function",
                    properties={
                        "name": "power",
                        "signature": "power(base, exp)",
                        "complexity": 1,
                        "start_line": 18,
                        "end_line": 20
                    }
                )
            ]
            
            relationships = [
                CodeRelationship(
                    source_id="sample.py",
                    target_id="fibonacci",
                    type="CONTAINS",
                    properties={"line_number": 2}
                ),
                CodeRelationship(
                    source_id="sample.py",
                    target_id="MathUtils",
                    type="CONTAINS",
                    properties={"line_number": 8}
                ),
                CodeRelationship(
                    source_id="MathUtils",
                    target_id="factorial",
                    type="CONTAINS",
                    properties={"line_number": 12}
                ),
                CodeRelationship(
                    source_id="MathUtils",
                    target_id="power",
                    type="CONTAINS",
                    properties={"line_number": 18}
                ),
                CodeRelationship(
                    source_id="fibonacci",
                    target_id="fibonacci",
                    type="CALLS",
                    properties={"line_number": 6, "frequency": 2}
                )
            ]
            
            # Store in graph store
            await graph_store.store_code_structure(nodes, relationships)
            logger.info("✅ Graph data stored successfully")
        else:
            logger.warning("Graph store not available, skipping graph data")

    if __name__ == "__main__":
        try:
            asyncio.run(setup_databases())
        except KeyboardInterrupt:
            logger.info("Setup interrupted by user")
        except Exception as e:
            logger.error(f"Setup failed: {e}")
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