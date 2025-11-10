"""
Load sample code data into RAG databases with embeddings
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

original_dir = os.getcwd()
os.chdir(backend_path)

try:
    from core.rag.chunker import CodeChunker
    from core.rag.embedders.smart_embedder import SmartEmbedder
    from core.rag.connections import get_connection_manager
    from utils.logger import logger
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)


async def main():
    """Load sample Python files with embeddings"""
    # ... [Sample data code remains the same] ...
    sample_files = [
        {
            "path": "sample_calculator.py",
            "language": "python",
            "code": '''
def add(a, b):
    """Add two numbers together and return the result"""
    return a + b

def subtract(a, b):
    """Subtract b from a and return the result"""
    return a - b

def multiply(a, b):
    """Multiply two numbers together and return the result"""
    return a * b

class Calculator:
    """A simple calculator class with basic operations"""
    def __init__(self):
        self.value = 0
    def add(self, x):
        self.value += x
        return self.value
    def reset(self):
        self.value = 0
'''
        },
        {
            "path": "sample_validator.py",
            "language": "python",
            "code": '''
import re
def validate_email(email):
    """Validate email address format using regex pattern"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
'''
        }
    ]
    
    print("=" * 70)
    print("Loading Sample Data with Embeddings")
    print("=" * 70)
    
    manager = None
    try:
        print("\n📦 Initializing components...")
        chunker = CodeChunker()
        embedder = SmartEmbedder()
        manager = await get_connection_manager()
        vector_store = await manager.get_vector_store()
        
        if not vector_store:
            print("❌ Vector store not available. Check Qdrant connection.")
            return

        total_chunks = 0
        for file_data in sample_files:
            print(f"\n📄 Processing: {file_data['path']}")
            chunks = await chunker.chunk_file(file_data['path'], file_data['code'], file_data['language'])
            print(f"   ✅ Created {len(chunks)} chunks")
            if not chunks: continue
            
            chunks_with_embeddings = await embedder.embed_chunks(chunks)
            successful = sum(1 for c in chunks_with_embeddings if c.embedding)
            print(f"   ✅ Generated {successful}/{len(chunks)} embeddings")
            
            if successful > 0:
                stored = await vector_store.store_chunks(chunks_with_embeddings)
                print(f"   ✅ Stored {len(stored)} chunks in Qdrant")
                total_chunks += len(stored)

        print("\n" + "=" * 70)
        print(f"✅ Complete! Loaded {total_chunks} chunks with embeddings")
        print("=" * 70)
        
        # Verify
        print("\n📊 Verifying...")
        from qdrant_client import QdrantClient
        try:
            qdrant = QdrantClient(url="http://localhost:6333")
            # ✅ Use qdrant.count() to avoid Pydantic errors
            count_result = qdrant.count(collection_name="code_chunks", exact=True)
            points_count = count_result.count
            
            print(f"   Vector points in Qdrant: {points_count}")
            
            if points_count > 0:
                print("\n🎉 SUCCESS! Embeddings are loaded and searchable!")
            else:
                print("\n⚠️  Warning: No points stored. Check JINA_API_KEY.")
        except Exception as e:
            print(f"   ⚠️  Could not verify Qdrant: {e}")
        
    finally:
        if manager:
            await manager.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Script failed: {e}")
        sys.exit(1)
    finally:
        os.chdir(original_dir)