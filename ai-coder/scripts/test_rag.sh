#!/bin/bash

echo "🧪 RAG Implementation Testing Suite"
echo "===================================="
echo ""

cd /workspaces/ai-coder/ai-coder

# 1. Check Docker
echo "1️⃣ Docker Containers"
echo "-------------------"
docker ps | grep -E "CONTAINER|qdrant|neo4j"
echo ""

# 2. Run setup
echo "2️⃣ Running Setup Script"
echo "----------------------"
python scripts/setup_rag_databases.py
echo ""

# 3. Check Qdrant
echo "3️⃣ Qdrant Collections"
echo "--------------------"
curl -s http://localhost:6333/collections | python -m json.tool
echo ""

# 4. Check Neo4j
echo "4️⃣ Neo4j Data"
echo "------------"
docker exec -it ai-coder-neo4j cypher-shell -u neo4j -p password123 \
    "MATCH (n) RETURN labels(n)[0] as type, count(n) as count" --format plain
echo ""

# 5. Run Python tests
echo "5️⃣ Python Module Tests"
echo "---------------------"
cd backend
python << 'EOF'
import asyncio
from core.rag.vector_store import VectorStore
from core.rag.graph_store import GraphStore

async def test():
    vs = VectorStore()
    gs = GraphStore()
    print(f"Vector Store: {'✅' if vs.health_check() else '❌'}")
    print(f"Graph Store: {'✅' if gs.health_check() else '❌'}")

asyncio.run(test())
EOF
echo ""

# 6. Run pytest
echo "6️⃣ RAG Tests"
echo "----------"
pytest tests/rag/ -v --no-cov --tb=short
echo ""

echo "===================================="
echo "✅ Testing Complete!"
echo "===================================="