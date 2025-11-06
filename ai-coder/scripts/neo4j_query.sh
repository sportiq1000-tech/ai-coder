#!/bin/bash

# Neo4j Query Helper
# Usage: ./scripts/neo4j_query.sh "MATCH (n) RETURN n LIMIT 5"

QUERY="${1:-MATCH (n) RETURN n LIMIT 10}"

echo "🔍 Running Neo4j Query:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$QUERY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

docker exec -it ai-coder-neo4j cypher-shell \
    -u neo4j \
    -p password123 \
    "$QUERY"