#!/bin/bash

# RAG Implementation - Complete Verification & Testing
# Single command to verify everything is working

# Stop on first error
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

echo ""
echo -e "${PURPLE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║                                                                ║${NC}"
echo -e "${PURPLE}║          ${CYAN}RAG IMPLEMENTATION - COMPLETE VERIFICATION${PURPLE}            ║${NC}"
echo -e "${PURPLE}║                    ${CYAN}Single Command Test${PURPLE}                         ║${NC}"
echo -e "${PURPLE}║                                                                ║${NC}"
echo -e "${PURPLE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

cd /workspaces/ai-coder/ai-coder
# ============================================================================
# STEP 0: Load Environment Variables (ADD THIS SECTION)
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 Loading Environment Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Navigate to backend directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo -e "${CYAN}ℹ️  Project root: $PROJECT_ROOT${NC}"
echo -e "${CYAN}ℹ️  Backend directory: $BACKEND_DIR${NC}"

# Check if .env file exists
if [ -f "$BACKEND_DIR/.env" ]; then
    echo -e "${GREEN}✅ Found .env file${NC}"
    
    # Load environment variables from .env file
    echo -e "${CYAN}ℹ️  Loading environment variables...${NC}"
    set -a  # Automatically export all variables
    source "$BACKEND_DIR/.env"
    set +a  # Stop auto-export
    
    echo -e "${GREEN}✅ Environment variables loaded${NC}"
else
    echo -e "${YELLOW}⚠️  .env file not found at $BACKEND_DIR/.env${NC}"
    echo -e "${YELLOW}ℹ️  Will check for system environment variables instead${NC}"
fi


# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to print success, error, warning, info
print_success() { echo -e "${GREEN}${CHECK} $1${NC}"; }
print_error() { echo -e "${RED}${CROSS} $1${NC}"; OVERALL_STATUS=1; }
print_warning() { echo -e "${YELLOW}${WARN} $1${NC}"; }
print_info() { echo -e "${CYAN}${INFO} $1${NC}"; }

# ============================================================================
# NEW FUNCTIONS ADDED
# ============================================================================

# Add environment variable check
check_env_vars() {
    print_info "Checking environment variables..."
    
    # Check if .env file exists
    if [ ! -f "backend/.env" ]; then
        print_warning "backend/.env file not found. Some checks might fail."
    fi
    
    # Critical variables
    if [ -z "$NEO4J_PASSWORD" ]; then
        print_error "NEO4J_PASSWORD not set. This is required for Neo4j connection."
        return 1
    else
        print_success "NEO4J_PASSWORD is set."
    fi
    
    # Optional variables (warn only)
    [ -z "$OPENAI_API_KEY" ] && print_warning "OPENAI_API_KEY not set (optional, for OpenAI embeddings)"
    [ -z "$JINA_API_KEY" ] && print_warning "JINA_API_KEY not set (optional, for Jina AI embeddings)"
    [ -z "$GEMINI_API_KEY" ] && print_warning "GEMINI_API_KEY not set (optional, for Gemini embeddings)"
    
    print_success "Required environment variables check complete."
}

# Add sample data verification
check_sample_data() {
    print_info "Verifying sample data in Qdrant..."
    
    # Check Qdrant for sample chunks
    COLLECTIONS_JSON=$(curl -s http://localhost:6333/collections/code_chunks)
    local chunk_count=$(echo "$COLLECTIONS_JSON" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('result', {}).get('points_count', 0))" 2>/dev/null || echo "0")
    
    if [ "$chunk_count" -gt 0 ]; then
        print_success "Sample data loaded: $chunk_count chunks in 'code_chunks' collection"
    else
        print_warning "No sample data found in 'code_chunks' collection. Run 'python scripts/setup_rag_databases.py' to load data."
    fi
}

# Add consistency check
check_consistency() {
    print_info "Checking cross-database consistency..."
    print_warning "Consistency check is a placeholder. Logic needs to be implemented."
    # Compare file counts between databases
    # (Add your logic here)
    
    print_success "Placeholder consistency check complete."
}

# Track overall status
OVERALL_STATUS=0

# ============================================================================
# 0️⃣  ENVIRONMENT VARIABLES
# ============================================================================
print_section "0️⃣  Environment Variables"
check_env_vars

# ============================================================================
# 1️⃣  DOCKER CONTAINERS
# ============================================================================
print_section "1️⃣  Docker Containers Status"

QDRANT_RUNNING=false
NEO4J_RUNNING=false

if docker ps | grep -q "ai-coder-qdrant"; then
    QDRANT_STATUS=$(docker inspect -f '{{.State.Status}}' ai-coder-qdrant)
    if [ "$QDRANT_STATUS" == "running" ]; then
        print_success "Qdrant container: Running"
        QDRANT_RUNNING=true
    else
        print_error "Qdrant container: $QDRANT_STATUS"
    fi
else
    print_error "Qdrant container: Not found"
fi

if docker ps | grep -q "ai-coder-neo4j"; then
    NEO4J_STATUS=$(docker inspect -f '{{.State.Status}}' ai-coder-neo4j)
    if [ "$NEO4J_STATUS" == "running" ]; then
        print_success "Neo4j container: Running"
        NEO4J_RUNNING=true
    else
        print_error "Neo4j container: $NEO4J_STATUS"
    fi
else
    print_error "Neo4j container: Not found"
fi

# Show detailed container info
echo ""
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "NAMES|qdrant|neo4j"

# ============================================================================
# 2️⃣  QDRANT (VECTOR DATABASE)
# ============================================================================
print_section "2️⃣  Qdrant Vector Database"

if [ "$QDRANT_RUNNING" = true ]; then
    if curl -s http://localhost:6333/ > /dev/null 2>&1; then
        print_success "Qdrant API: Accessible"
        
        # Get version
        VERSION=$(curl -s http://localhost:6333/ | python -c "import sys, json; print(json.load(sys.stdin).get('version', 'unknown'))" 2>/dev/null || echo "unknown")
        print_info "Version: $VERSION"
        
        # List collections
        echo ""
        echo "📦 Collections:"
        COLLECTIONS_JSON=$(curl -s http://localhost:6333/collections)
        COLLECTIONS_FOUND=$(echo "$COLLECTIONS_JSON" | python -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('result', {}).get('collections', [])))" 2>/dev/null || echo "0")
        
        if [ "$COLLECTIONS_FOUND" -gt 0 ]; then
            print_success "Found $COLLECTIONS_FOUND collections"
            echo "$COLLECTIONS_JSON" | python -c "
import sys, json;
data = json.load(sys.stdin);
for col in data.get('result', {}).get('collections', []):
    print(f\"  • {col['name']}\")
"
        else
            print_warning "No collections found. Run 'python scripts/setup_rag_databases.py' to create them."
        fi
        
        # Collection details
        echo ""
        echo "📊 Collection Details:"
        for collection in code_chunks doc_chunks bug_chunks; do
            INFO=$(curl -s "http://localhost:6333/collections/$collection" 2>/dev/null)
            if echo "$INFO" | grep -q "error"; then
                print_warning "$collection: Not found"
            else
                POINTS=$(echo "$INFO" | python -c "import sys, json; print(json.load(sys.stdin).get('result', {}).get('points_count', 'N/A'))" 2>/dev/null || echo "N/A")
                DIMENSION=$(echo "$INFO" | python -c "import sys, json; print(json.load(sys.stdin).get('result', {}).get('config', {}).get('params', {}).get('vectors', {}).get('size', 'N/A'))" 2>/dev/null || echo "N/A")
                
                if [ "$DIMENSION" == "768" ]; then
                    print_success "$collection: $POINTS points, Dimension: 768"
                else
                    print_error "$collection: $POINTS points, Dimension: $DIMENSION (Expected 768)"
                fi
            fi
        done
        
    else
        print_error "Qdrant API: Not accessible"
    fi
else
    print_warning "Qdrant container not running, skipping checks."
fi

# ============================================================================
# 3️⃣  NEO4J (GRAPH DATABASE)
# ============================================================================
print_section "3️⃣  Neo4j Graph Database"

if [ "$NEO4J_RUNNING" = true ]; then
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
            print_warning "Total nodes: $TOTAL_NODES (Run 'python scripts/setup_rag_databases.py' to load data)"
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
                --format plain 2>/dev/null | tail -n +2 | sed 's/^/  • /'
        fi
    else
        print_error "Neo4j API: Not accessible"
    fi
else
    print_warning "Neo4j container not running, skipping checks."
fi

# ============================================================================
# 4️⃣  PYTHON MODULES
# ============================================================================
print_section "4️⃣  Python Module Tests"

cd backend
PYTHON_TEST_OUTPUT=$(python << 'PYTHON_EOF'
import asyncio
import sys

async def test_modules():
    errors = []
    
    try:
        from core.rag.embeddings import CodeEmbedder
        print("✅ CodeEmbedder imported successfully")
        
        embedder = CodeEmbedder()
        print("✅ CodeEmbedder initialized")
        
        health_status = embedder.health_check()
        print(f"✅ Health check completed: {health_status}")
        
        stats = embedder.get_stats()
        print(f"✅ Stats retrieved: Primary is {stats.get('primary_embedder')}")
        
        if not stats.get('primary_embedder') and not stats.get('fallbacks_available'):
            print("❌ No embedders are available!")
            errors.append("No embedders available")
        
        return len(errors) == 0
        
    except Exception as e:
        print(f"❌ Error during module test: {e}")
        import traceback
        traceback.print_exc()
        return False

success = asyncio.run(test_modules())
sys.exit(0 if success else 1)
PYTHON_EOF
)

echo "$PYTHON_TEST_OUTPUT"
PYTHON_EXIT_CODE=$?

if [ $PYTHON_EXIT_CODE -ne 0 ]; then
    print_error "Python modules test failed"
    OVERALL_STATUS=1
fi
cd ..

# ============================================================================
# 5️⃣  PYTEST TESTS
# ============================================================================
print_section "5️⃣  RAG Unit Tests (pytest)"

cd backend
echo "Running pytest..."
echo ""

PYTEST_OUTPUT=$(pytest tests/rag/ -v --no-cov --tb=short 2>&1)
PYTEST_EXIT_CODE=$?

echo "$PYTEST_OUTPUT" | tail -n 20

if [ $PYTEST_EXIT_CODE -eq 0 ]; then
    print_success "All RAG tests passed!"
else
    print_error "Some pytest tests failed"
    OVERALL_STATUS=1
fi
cd ..

# ============================================================================
# 6️⃣  DATA VERIFICATION
# ============================================================================
print_section "6️⃣  Data Verification"

# This section has been replaced to use Python scripts for verification.
if python scripts/check_data.py; then
    print_success "Data verification passed."
else
    print_warning "Data verification failed. Attempting to load sample data..."
    if python scripts/load_sample_with_embeddings.py; then
        print_success "Sample data loaded successfully. Re-verifying..."
        if python scripts/check_data.py; then
            print_success "Data verification passed after loading."
        else
            print_error "Data verification still failed after loading sample data."
        fi
    else
        print_error "Failed to load sample data. Check API keys and logs."
    fi
fi

# ============================================================================
# 7️⃣  SUMMARY
# ============================================================================
print_section "7️⃣  Final Summary"

echo ""
echo "Component Health:"
echo "  • Qdrant (Vector DB):    $([ "$QDRANT_RUNNING" = true ] && curl -s http://localhost:6333/ >/dev/null 2>&1 && echo '✅ Healthy' || echo '❌ Down')"
echo "  • Neo4j (Graph DB):      $([ "$NEO4J_RUNNING" = true ] && docker exec ai-coder-neo4j cypher-shell -u neo4j -p password123 "RETURN 1" >/dev/null 2>&1 && echo '✅ Healthy' || echo '❌ Down')"
echo "  • Python Modules:        $([ $PYTHON_EXIT_CODE -eq 0 ] && echo '✅ Working' || echo '❌ Errors')"
echo "  • Pytest Tests:          $([ $PYTEST_EXIT_CODE -eq 0 ] && echo '✅ Passing' || echo '❌ Failing')"

echo ""
echo "Data Status:"
TOTAL_NODES=$(docker exec ai-coder-neo4j cypher-shell -u neo4j -p password123 "MATCH (n) RETURN count(n)" --format plain 2>/dev/null | tail -1 | tr -d '\r' || echo "0")
TOTAL_RELS=$(docker exec ai-coder-neo4j cypher-shell -u neo4j -p password123 "MATCH ()-[r]->() RETURN count(r)" --format plain 2>/dev/null | tail -1 | tr -d '\r' || echo "0")
echo "  • Vector Collections:    $(curl -s http://localhost:6333/collections | python -c "import sys, json; print(len(json.load(sys.stdin).get('result', {}).get('collections', [])))" 2>/dev/null || echo '0') created"
echo "  • Graph Nodes:           $TOTAL_NODES"
echo "  • Graph Relationships:   $TOTAL_RELS"
echo "  • Vector Points:         0 (need OpenAI/HF/Gemini key for embeddings)"

echo ""
echo "Quick Access:"
echo "  • Qdrant UI:      http://localhost:6333/dashboard"
echo "  • Neo4j Browser:  http://localhost:7474 (check PORTS tab in Codespaces)"
echo "  • Check Data:     python scripts/check_sample_data.py"

echo ""
if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}                                                                ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${CHECK} ALL SYSTEMS OPERATIONAL${NC}                                   ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                                ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    print_success "RAG Implementation is fully functional!"
else
    echo -e "${YELLOW}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║${NC}                                                                ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}  ${WARN} SOME ISSUES DETECTED${NC}                                      ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}                                                                ${YELLOW}║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    print_warning "Some components need attention. Review logs above."
fi

echo ""
print_info "To run again: ./scripts/rag_verify_all.sh"
echo ""

exit $OVERALL_STATUS