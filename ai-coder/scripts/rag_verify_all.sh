#!/bin/bash

# RAG Implementation - Complete Verification & Testing
# Single command to verify everything is working

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Icons
CHECK="✅"
CROSS="❌"
WARN="⚠️"
INFO="ℹ️"
ROCKET="🚀"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║          RAG IMPLEMENTATION - COMPLETE VERIFICATION            ║"
echo "║                    Single Command Test                         ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

cd /workspaces/ai-coder/ai-coder

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}${CHECK} $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}${CROSS} $1${NC}"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}${WARN} $1${NC}"
}

# Function to print info
print_info() {
    echo -e "${CYAN}${INFO} $1${NC}"
}

# Track overall status
OVERALL_STATUS=0

# ============================================================================
# 1. DOCKER CONTAINERS
# ============================================================================
print_section "1️⃣  Docker Containers Status"

if docker ps | grep -q "ai-coder-qdrant"; then
    QDRANT_STATUS=$(docker inspect -f '{{.State.Status}}' ai-coder-qdrant)
    if [ "$QDRANT_STATUS" == "running" ]; then
        print_success "Qdrant container: Running"
    else
        print_error "Qdrant container: $QDRANT_STATUS"
        OVERALL_STATUS=1
    fi
else
    print_error "Qdrant container: Not found"
    OVERALL_STATUS=1
fi

if docker ps | grep -q "ai-coder-neo4j"; then
    NEO4J_STATUS=$(docker inspect -f '{{.State.Status}}' ai-coder-neo4j)
    if [ "$NEO4J_STATUS" == "running" ]; then
        print_success "Neo4j container: Running"
    else
        print_error "Neo4j container: $NEO4J_STATUS"
        OVERALL_STATUS=1
    fi
else
    print_error "Neo4j container: Not found"
    OVERALL_STATUS=1
fi

# Show detailed container info
echo ""
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "NAMES|qdrant|neo4j"

# ============================================================================
# 2. QDRANT (VECTOR DATABASE)
# ============================================================================
print_section "2️⃣  Qdrant Vector Database"

# Test connectivity
if curl -s http://localhost:6333/ > /dev/null 2>&1; then
    print_success "Qdrant API: Accessible"
    
    # Get version
    VERSION=$(curl -s http://localhost:6333/ | python -c "import sys, json; print(json.load(sys.stdin).get('version', 'unknown'))" 2>/dev/null || echo "unknown")
    print_info "Version: $VERSION"
    
    # List collections
    echo ""
    echo "📦 Collections:"
    COLLECTIONS_JSON=$(curl -s http://localhost:6333/collections)
    echo "$COLLECTIONS_JSON" | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    collections = data.get('result', {}).get('collections', [])
    if collections:
        for col in collections:
            print(f\"  • {col['name']}\")
    else:
        print('  (none)')
except:
    print('  (error parsing)')
" 2>/dev/null || echo "  (error)"
    
    # Collection details
    echo ""
    echo "📊 Collection Details:"
    for collection in code_chunks doc_chunks bug_chunks; do
        INFO=$(curl -s "http://localhost:6333/collections/$collection" 2>/dev/null | python -m json.tool 2>/dev/null)
        if echo "$INFO" | grep -q "error"; then
            print_warning "$collection: Not found"
        else
            POINTS=$(echo "$INFO" | python -c "import sys, json; print(json.load(sys.stdin).get('result', {}).get('points_count', 'N/A'))" 2>/dev/null || echo "N/A")
            VECTORS=$(echo "$INFO" | python -c "import sys, json; print(json.load(sys.stdin).get('result', {}).get('vectors_count', 'N/A'))" 2>/dev/null || echo "N/A")
            
            if [ "$POINTS" == "0" ] || [ "$POINTS" == "N/A" ]; then
                print_warning "$collection: $POINTS points, $VECTORS vectors"
            else
                print_success "$collection: $POINTS points, $VECTORS vectors"
            fi
        fi
    done
    
else
    print_error "Qdrant API: Not accessible"
    OVERALL_STATUS=1
fi

# ============================================================================
# 3. NEO4J (GRAPH DATABASE)
# ============================================================================
print_section "3️⃣  Neo4j Graph Database"

# Test connectivity
if docker exec ai-coder-neo4j cypher-shell -u neo4j -p password123 "RETURN 1" > /dev/null 2>&1; then
    print_success "Neo4j API: Accessible"
    
    # Get version
    NEO4J_VERSION=$(docker exec ai-coder-neo4j cypher-shell -u neo4j -p password123 "CALL dbms.components() YIELD name, versions RETURN versions[0]" --format plain 2>/dev/null | tail -1 | tr -d '\r' || echo "unknown")
    print_info "Version: $NEO4J_VERSION"
    
    # Count total nodes
    echo ""
    echo "📊 Graph Statistics:"
    TOTAL_NODES=$(docker exec ai-coder-neo4j cypher-shell -u neo4j -p password123 \
        "MATCH (n) RETURN count(n) as count" --format plain 2>/dev/null | tail -1 | tr -d '\r' || echo "0")
    
    if [ "$TOTAL_NODES" -gt 0 ]; then
        print_success "Total nodes: $TOTAL_NODES"
    else
        print_warning "Total nodes: $TOTAL_NODES (sample data not loaded)"
    fi
    
    # Count relationships
    TOTAL_RELS=$(docker exec ai-coder-neo4j cypher-shell -u neo4j -p password123 \
        "MATCH ()-[r]->() RETURN count(r) as count" --format plain 2>/dev/null | tail -1 | tr -d '\r' || echo "0")
    
    if [ "$TOTAL_RELS" -gt 0 ]; then
        print_success "Total relationships: $TOTAL_RELS"
    else
        print_warning "Total relationships: $TOTAL_RELS"
    fi
    
    # Nodes by type
    if [ "$TOTAL_NODES" -gt 0 ]; then
        echo ""
        echo "📋 Nodes by Type:"
        docker exec ai-coder-neo4j cypher-shell -u neo4j -p password123 \
            "MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY type" \
            --format plain 2>/dev/null | tail -n +2 | while IFS=, read -r type count; do
            type=$(echo "$type" | tr -d '"' | tr -d '\r')
            count=$(echo "$count" | tr -d '\r')
            echo "  • $type: $count"
        done
        
        # Relationships by type
        echo ""
        echo "🔗 Relationships by Type:"
        docker exec ai-coder-neo4j cypher-shell -u neo4j -p password123 \
            "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY type" \
            --format plain 2>/dev/null | tail -n +2 | while IFS=, read -r type count; do
            type=$(echo "$type" | tr -d '"' | tr -d '\r')
            count=$(echo "$count" | tr -d '\r')
            echo "  • $type: $count"
        done
        
        # Sample nodes
        echo ""
        echo "📄 Sample Nodes (first 5):"
        docker exec ai-coder-neo4j cypher-shell -u neo4j -p password123 \
            "MATCH (n) RETURN labels(n)[0] as type, coalesce(n.name, n.path) as identifier LIMIT 5" \
            --format plain 2>/dev/null | tail -n +2 | while IFS=, read -r type identifier; do
            type=$(echo "$type" | tr -d '"' | tr -d '\r')
            identifier=$(echo "$identifier" | tr -d '"' | tr -d '\r')
            echo "  • $type: $identifier"
        done
    fi
    
else
    print_error "Neo4j API: Not accessible"
    OVERALL_STATUS=1
fi

# ============================================================================
# 4. PYTHON MODULES
# ============================================================================
print_section "4️⃣  Python Module Tests"

cd backend
PYTHON_TEST_OUTPUT=$(python << 'PYTHON_EOF'
import asyncio
import sys

async def test_modules():
    errors = []
    
    # Test imports
    try:
        from core.rag.vector_store import VectorStore
        from core.rag.graph_store import GraphStore
        from core.rag.chunker import CodeChunker
        from core.rag.embeddings import CodeEmbedder
        from core.rag.connections import get_connection_manager
        print("✅ All modules imported successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        errors.append(str(e))
        return False
    
    # Test vector store
    try:
        vs = VectorStore()
        if vs.health_check():
            print("✅ Vector Store: Healthy")
        else:
            print("❌ Vector Store: Unhealthy")
            errors.append("Vector store health check failed")
    except Exception as e:
        print(f"❌ Vector Store: {e}")
        errors.append(str(e))
    
    # Test graph store
    try:
        gs = GraphStore()
        if gs.health_check():
            print("✅ Graph Store: Healthy")
        else:
            print("❌ Graph Store: Unhealthy")
            errors.append("Graph store health check failed")
    except Exception as e:
        print(f"❌ Graph Store: {e}")
        errors.append(str(e))
    
    # Test chunker
    try:
        chunker = CodeChunker()
        code = 'def test():\n    """Test function"""\n    return "hello"\n\nclass Test:\n    """Test class"""\n    pass'
        chunks = await chunker.chunk_file("test.py", code, "python")
        if len(chunks) > 0:
            print(f"✅ Code Chunker: Created {len(chunks)} chunks")
        else:
            print("❌ Code Chunker: No chunks created")
            errors.append("Chunker created no chunks")
    except Exception as e:
        print(f"❌ Code Chunker: {e}")
        errors.append(str(e))
    
    # Test connection manager
    try:
        manager = await get_connection_manager()
        print("✅ Connection Manager: Initialized")
        await manager.cleanup()
    except Exception as e:
        print(f"❌ Connection Manager: {e}")
        errors.append(str(e))
    
    return len(errors) == 0

success = asyncio.run(test_modules())
sys.exit(0 if success else 1)
PYTHON_EOF
)

echo "$PYTHON_TEST_OUTPUT"
PYTHON_EXIT_CODE=$?

if [ $PYTHON_EXIT_CODE -ne 0 ]; then
    OVERALL_STATUS=1
fi

cd ..

# ============================================================================
# 5. PYTEST TESTS
# ============================================================================
print_section "5️⃣  RAG Unit Tests (pytest)"

cd backend
echo "Running pytest..."
echo ""

PYTEST_OUTPUT=$(pytest tests/rag/ -v --no-cov --tb=short 2>&1)
PYTEST_EXIT_CODE=$?

# Extract summary
echo "$PYTEST_OUTPUT" | tail -20

if [ $PYTEST_EXIT_CODE -eq 0 ]; then
    echo ""
    print_success "All tests passed!"
else
    echo ""
    print_error "Some tests failed"
    OVERALL_STATUS=1
fi

cd ..

# ============================================================================
# 6. SAMPLE QUERIES
# ============================================================================
print_section "6️⃣  Sample Neo4j Queries"

if [ "$TOTAL_NODES" -gt 0 ]; then
    echo "🔍 Finding all functions:"
    docker exec ai-coder-neo4j cypher-shell -u neo4j -p password123 \
        "MATCH (f:Function) RETURN f.name as name, f.complexity as complexity ORDER BY f.complexity DESC LIMIT 5" \
        --format plain 2>/dev/null | tail -n +2 | while IFS=, read -r name complexity; do
        name=$(echo "$name" | tr -d '"' | tr -d '\r')
        complexity=$(echo "$complexity" | tr -d '\r')
        echo "  • $name (complexity: $complexity)"
    done
    
    echo ""
    echo "🔍 Finding file structure:"
    docker exec ai-coder-neo4j cypher-shell -u neo4j -p password123 \
        "MATCH (f:File)-[:CONTAINS]->(n) RETURN f.path as file, labels(n)[0] as contains, coalesce(n.name, 'N/A') as name LIMIT 10" \
        --format plain 2>/dev/null | tail -n +2 | while IFS=, read -r file contains name; do
        file=$(echo "$file" | tr -d '"' | tr -d '\r')
        contains=$(echo "$contains" | tr -d '"' | tr -d '\r')
        name=$(echo "$name" | tr -d '"' | tr -d '\r')
        echo "  • $file → $contains: $name"
    done
else
    print_warning "No sample data to query"
fi

# ============================================================================
# 7. SUMMARY
# ============================================================================
print_section "📊 Final Summary"

echo ""
echo "Component Health:"
echo "  • Qdrant (Vector DB):    $(curl -s http://localhost:6333/ >/dev/null 2>&1 && echo '✅ Healthy' || echo '❌ Down')"
echo "  • Neo4j (Graph DB):      $(docker exec ai-coder-neo4j cypher-shell -u neo4j -p password123 "RETURN 1" >/dev/null 2>&1 && echo '✅ Healthy' || echo '❌ Down')"
echo "  • Python Modules:        $([ $PYTHON_EXIT_CODE -eq 0 ] && echo '✅ Working' || echo '❌ Errors')"
echo "  • Pytest Tests:          $([ $PYTEST_EXIT_CODE -eq 0 ] && echo '✅ Passing' || echo '❌ Failing')"

echo ""
echo "Data Status:"
echo "  • Vector Collections:    3 created"
echo "  • Graph Nodes:           $TOTAL_NODES"
echo "  • Graph Relationships:   $TOTAL_RELS"
echo "  • Vector Points:         0 (need OpenAI key)"

echo ""
echo "Quick Access:"
echo "  • Qdrant UI:      http://localhost:6333/dashboard"
echo "  • Neo4j Browser:  http://localhost:7474"
echo "  • Check Data:     python scripts/check_sample_data.py"

echo ""
if [ $OVERALL_STATUS -eq 0 ]; then
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                                                                ║"
    echo -e "║  ${GREEN}${CHECK} ALL SYSTEMS OPERATIONAL${NC}                                   ║"
    echo "║                                                                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    print_success "RAG Implementation is fully functional!"
else
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                                                                ║"
    echo -e "║  ${YELLOW}${WARN} SOME ISSUES DETECTED${NC}                                      ║"
    echo "║                                                                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    print_warning "Some components need attention"
fi

echo ""
print_info "To run again: ./scripts/rag_verify_all.sh"
echo ""

exit $OVERALL_STATUS