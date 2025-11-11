"""
Load sample code data into RAG databases with embeddings
"""
import asyncio
import sys
import os
from pathlib import Path
from typing import List

# Setup Python path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

original_dir = os.getcwd()
os.chdir(backend_path)

try:
    from core.rag.chunker import CodeChunker
    from core.rag.embedders.smart_embedder import SmartEmbedder
    from core.rag.connections import get_connection_manager
    from schemas.rag_schemas import CodeChunk
    from core.rag.graph_store import GraphStore
    from utils.logger import logger
    from utils.config import get_settings # Import get_settings
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)


async def store_chunks_in_graph(graph_store: GraphStore, chunks: List[CodeChunk], database_name: str) -> int:
    """Stores code chunks as nodes and relationships in Neo4j."""
    if not chunks or not graph_store:
        return 0

    nodes_to_create = []
    for chunk in chunks:
        if chunk.chunk_type in ("functiondef", "classdef", "function", "class", "function_or_class"):
            nodes_to_create.append({
                'file_path': chunk.file_path,
                'chunk_id': chunk.id,
                'chunk_type': chunk.chunk_type,
                'name': chunk.metadata.get('name', 'unknown'),
                'start_line': chunk.start_line,
                'end_line': chunk.end_line
            })

    if not nodes_to_create:
        return 0

    query = """
    UNWIND $nodes as node_data
    MERGE (f:File {path: node_data.file_path})
    FOREACH (_ IN CASE WHEN node_data.chunk_type IN ['functiondef', 'function', 'function_or_class'] THEN [1] ELSE [] END |
        MERGE (fn:Function {id: node_data.chunk_id})
        ON CREATE SET fn.name = node_data.name, fn.start_line = node_data.start_line, fn.end_line = node_data.end_line
        MERGE (f)-[:CONTAINS]->(fn)
    )
    FOREACH (_ IN CASE WHEN node_data.chunk_type IN ['classdef', 'class'] THEN [1] ELSE [] END |
        MERGE (c:Class {id: node_data.chunk_id})
        ON CREATE SET c.name = node_data.name, c.start_line = node_data.start_line, c.end_line = node_data.end_line
        MERGE (f)-[:CONTAINS]->(c)
    )
    """

    try:
        # ✅ FIX: Use the database_name parameter passed into the function
        with graph_store.driver.session(database=database_name) as session:
            session.run(query, nodes=nodes_to_create)
        return len(nodes_to_create)
    except Exception as e:
        logger.error(f"Failed to store data in Neo4j: {e}")
        return 0


async def main():
    """Load sample Python files with embeddings"""
    
    # ... [Sample data remains the same] ...
    sample_files = [
        {
            "path": "sample_calculator.py",
            "language": "python",
            "code": '''
def add(a, b):
    """Add two numbers together"""
    return a + b
def subtract(a, b):
    """Subtract b from a"""
    return a - b
class Calculator:
    """A simple calculator class"""
    def __init__(self):
        self.value = 0
'''
        },
        {
            "path": "sample_validator.js",
            "language": "javascript",
            "code": '''
function validateEmail(email) {
    // Basic email validation regex
    const re = /\\S+@\\S+\\.\\S+/;
    return re.test(email);
}
'''
        }
    ]
    
    print("=" * 70)
    print("Loading Sample Data into RAG Databases (Vector + Graph)")
    print("=" * 70)
    
    manager = None
    try:
        print("\n📦 Initializing components...")
        chunker = CodeChunker()
        embedder = SmartEmbedder()
        settings = get_settings() # Get settings once
        manager = await get_connection_manager()
        vector_store = await manager.get_vector_store()
        graph_store = await manager.get_graph_store()
        
        if not vector_store or not graph_store:
            print("❌ Database stores not available. Aborting.")
            return

        total_vectors = 0
        total_nodes = 0
        
        for file_data in sample_files:
            print(f"\n📄 Processing: {file_data['path']}")
            chunks = await chunker.chunk_file(file_data['path'], file_data['code'], file_data['language'])
            print(f"   - Created {len(chunks)} chunks")
            if not chunks: continue
            
            chunks_with_embeddings = await embedder.embed_chunks(chunks)
            successful = sum(1 for c in chunks_with_embeddings if c.embedding)
            print(f"   - Generated {successful}/{len(chunks)} embeddings")
            
            if successful > 0:
                stored_vectors = await vector_store.store_chunks(chunks_with_embeddings)
                print(f"   - Stored {len(stored_vectors)} vector points in Qdrant")
                total_vectors += len(stored_vectors)
                
                # ✅ FIX: Pass settings.NEO4J_DATABASE to the function
                stored_nodes = await store_chunks_in_graph(graph_store, chunks_with_embeddings, settings.NEO4J_DATABASE)
                print(f"   - Stored {stored_nodes} graph nodes in Neo4j")
                total_nodes += stored_nodes

        print("\n" + "=" * 70)
        print(f"✅ Complete! Loaded {total_vectors} vectors and {total_nodes} graph nodes.")
        print("=" * 70)
        
    finally:
        if manager:
            await manager.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        os.chdir(original_dir)