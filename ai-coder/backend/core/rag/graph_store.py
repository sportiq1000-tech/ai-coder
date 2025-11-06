"""
Graph Store Implementation using Neo4j
Manages code relationships and structural information
"""

from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, Driver
from utils.logger import logger
from utils.config import get_settings
from schemas.rag_schemas import CodeNode, CodeRelationship, GraphQueryResult

class GraphStore:
    """
    Manages graph storage and retrieval operations with Neo4j
    """
    
    def __init__(self):
        """Initialize Neo4j driver"""
        self.settings = get_settings()
        self.driver = None
        self._initialize_driver()
        self._create_constraints()
    
    def _initialize_driver(self):
        """Initialize Neo4j driver with authentication"""
        try:
            # FIX: Use UPPERCASE attribute names to match Settings class
            neo4j_uri = getattr(self.settings, 'NEO4J_URI', None)
            neo4j_user = getattr(self.settings, 'NEO4J_USER', 'neo4j')
            neo4j_password = getattr(self.settings, 'NEO4J_PASSWORD', None)
            neo4j_database = getattr(self.settings, 'NEO4J_DATABASE', 'neo4j')
            
            logger.info(f"Attempting to connect to Neo4j at: {neo4j_uri}")
            
            if not neo4j_uri or not neo4j_password:
                logger.warning("Neo4j not configured, graph features will be unavailable")
                return
            
            self.driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50
            )
            
            # Test connection
            with self.driver.session(database=neo4j_database) as session:
                session.run("RETURN 1")
            logger.info("✅ Neo4j driver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {e}")
            raise
    
    def _create_constraints(self):
        """Create database constraints and indexes"""
        if not self.driver:
            return
            
        # FIX: Use UPPERCASE attribute name
        neo4j_database = getattr(self.settings, 'NEO4J_DATABASE', 'neo4j')
        
        constraints = [
            "CREATE CONSTRAINT file_path_unique IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE",
            "CREATE CONSTRAINT function_id_unique IF NOT EXISTS FOR (fn:Function) REQUIRE fn.id IS UNIQUE",
            "CREATE CONSTRAINT class_id_unique IF NOT EXISTS FOR (c:Class) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT module_name_unique IF NOT EXISTS FOR (m:Module) REQUIRE m.name IS UNIQUE"
        ]
        
        indexes = [
            "CREATE INDEX function_name_index IF NOT EXISTS FOR (fn:Function) ON (fn.name)",
            "CREATE INDEX class_name_index IF NOT EXISTS FOR (c:Class) ON (c.name)",
            "CREATE INDEX file_language_index IF NOT EXISTS FOR (f:File) ON (f.language)",
            "CREATE INDEX function_complexity_index IF NOT EXISTS FOR (fn:Function) ON (fn.complexity)"
        ]
        
        with self.driver.session(database=neo4j_database) as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.debug(f"Created constraint: {constraint}")
                except Exception as e:
                    logger.debug(f"Constraint already exists or failed: {e}")
            
            for index in indexes:
                try:
                    session.run(index)
                    logger.debug(f"Created index: {index}")
                except Exception as e:
                    logger.debug(f"Index already exists or failed: {e}")
    
    async def store_code_structure(
        self, 
        nodes: List[CodeNode], 
        relationships: List[CodeRelationship]
    ):
        """
        Store code nodes and relationships in graph
        
        Args:
            nodes: List of code nodes (files, functions, classes)
            relationships: List of relationships between nodes
        """
        if not self.driver:
            logger.warning("Neo4j not available, skipping graph storage")
            return
            
        # FIX: Use UPPERCASE attribute name
        neo4j_database = getattr(self.settings, 'NEO4J_DATABASE', 'neo4j')
        
        with self.driver.session(database=neo4j_database) as session:
            # Store nodes
            for node in nodes:
                try:
                    if node.type == "file":
                        query = """
                        MERGE (f:File {path: $path})
                        SET f.language = $language, 
                            f.lines_of_code = $lines_of_code,
                            f.last_modified = $last_modified, 
                            f.metadata = $metadata
                        """
                        params = {
                            "path": node.id,
                            "language": node.properties.get("language"),
                            "lines_of_code": node.properties.get("lines_of_code"),
                            "last_modified": node.properties.get("last_modified"),
                            "metadata": str(node.properties.get("metadata", {}))
                        }
                    elif node.type == "function":
                        query = """
                        MERGE (f:Function {id: $id})
                        SET f.name = $name, 
                            f.signature = $signature, 
                            f.complexity = $complexity,
                            f.start_line = $start_line, 
                            f.end_line = $end_line,
                            f.has_tests = $has_tests, 
                            f.metadata = $metadata
                        """
                        params = {
                            "id": node.id,
                            "name": node.properties.get("name"),
                            "signature": node.properties.get("signature"),
                            "complexity": node.properties.get("complexity"),
                            "start_line": node.properties.get("start_line"),
                            "end_line": node.properties.get("end_line"),
                            "has_tests": node.properties.get("has_tests"),
                            "metadata": str(node.properties.get("metadata", {}))
                        }
                    elif node.type == "class":
                        query = """
                        MERGE (c:Class {id: $id})
                        SET c.name = $name, 
                            c.signature = $signature, 
                            c.start_line = $start_line,
                            c.end_line = $end_line, 
                            c.parent_class = $parent_class,
                            c.interfaces = $interfaces, 
                            c.metadata = $metadata
                        """
                        params = {
                            "id": node.id,
                            "name": node.properties.get("name"),
                            "signature": node.properties.get("signature"),
                            "start_line": node.properties.get("start_line"),
                            "end_line": node.properties.get("end_line"),
                            "parent_class": node.properties.get("parent_class"),
                            "interfaces": str(node.properties.get("interfaces", [])),
                            "metadata": str(node.properties.get("metadata", {}))
                        }
                    else:
                        continue
                    
                    session.run(query, params)
                except Exception as e:
                    logger.error(f"Failed to store node {node.id}: {e}")
            
            # Store relationships
            for rel in relationships:
                try:
                    if rel.type == "CONTAINS":
                        query = """
                        MATCH (parent), (child)
                        WHERE parent.path = $source_id OR parent.id = $source_id
                        AND (child.path = $target_id OR child.id = $target_id)
                        MERGE (parent)-[r:CONTAINS]->(child)
                        SET r.line_number = $line_number, r.metadata = $metadata
                        """
                    elif rel.type == "CALLS":
                        query = """
                        MATCH (caller:Function), (callee:Function)
                        WHERE caller.id = $source_id AND callee.id = $target_id
                        MERGE (caller)-[r:CALLS]->(callee)
                        SET r.line_number = $line_number, 
                            r.frequency = $frequency, 
                            r.metadata = $metadata
                        """
                    elif rel.type == "IMPORTS":
                        query = """
                        MATCH (importer:File), (imported:Module)
                        WHERE importer.path = $source_id AND imported.name = $target_id
                        MERGE (importer)-[r:IMPORTS]->(imported)
                        SET r.import_type = $import_type, 
                            r.line_number = $line_number, 
                            r.metadata = $metadata
                        """
                    elif rel.type == "EXTENDS":
                        query = """
                        MATCH (child:Class), (parent:Class)
                        WHERE child.id = $source_id AND parent.id = $target_id
                        MERGE (child)-[r:EXTENDS]->(parent)
                        SET r.metadata = $metadata
                        """
                    else:
                        continue
                    
                    params = {
                        "source_id": rel.source_id,
                        "target_id": rel.target_id,
                        "line_number": rel.properties.get("line_number"),
                        "frequency": rel.properties.get("frequency"),
                        "import_type": rel.properties.get("import_type"),
                        "metadata": str(rel.properties.get("metadata", {}))
                    }
                    
                    session.run(query, params)
                except Exception as e:
                    logger.error(f"Failed to store relationship {rel.type}: {e}")
        
        logger.info(f"Stored {len(nodes)} nodes and {len(relationships)} relationships")
    
    async def find_dependencies(
        self, 
        node_id: str, 
        depth: int = 2
    ) -> List[GraphQueryResult]:
        """
        Find all dependencies for a given node
        
        Args:
            node_id: ID of the starting node
            depth: Maximum depth of traversal
            
        Returns:
            List of dependent nodes with paths
        """
        if not self.driver:
            logger.warning("Neo4j not available")
            return []
            
        # FIX: Use UPPERCASE attribute name
        neo4j_database = getattr(self.settings, 'NEO4J_DATABASE', 'neo4j')
        
        query = """
        MATCH path = (start)-[:CALLS|IMPORTS|EXTENDS*1..$depth]->(end)
        WHERE start.id = $node_id OR start.path = $node_id
        RETURN DISTINCT end, 
               length(path) as depth, 
               [node in nodes(path) | coalesce(node.id, node.path)] as path_nodes
        ORDER BY depth, end.name
        LIMIT 100
        """
        
        with self.driver.session(database=neo4j_database) as session:
            result = session.run(query, node_id=node_id, depth=depth)
            
            dependencies = []
            for record in result:
                end_node = record["end"]
                node_id = end_node.get("id") or end_node.get("path")
                node_type = list(end_node.labels)[0] if end_node.labels else "Unknown"
                
                dependencies.append(GraphQueryResult(
                    id=node_id,
                    type=node_type,
                    properties=dict(end_node),
                    path=record["path_nodes"],
                    depth=record["depth"]
                ))
            
            return dependencies
    
    async def analyze_impact(self, node_id: str) -> Dict[str, Any]:
        """
        Analyze the impact of changing a node
        
        Args:
            node_id: ID of the node to analyze
            
        Returns:
            Impact analysis results
        """
        if not self.driver:
            logger.warning("Neo4j not available")
            return {}
            
        # FIX: Use UPPERCASE attribute name
        neo4j_database = getattr(self.settings, 'NEO4J_DATABASE', 'neo4j')
        
        queries = {
            "direct_dependencies": """
                MATCH (n)-[:CALLS]->(dep)
                WHERE n.id = $node_id OR n.path = $node_id
                RETURN count(dep) as count
            """,
            "dependents": """
                MATCH (dep)-[:CALLS]->(n)
                WHERE n.id = $node_id OR n.path = $node_id
                RETURN count(dep) as count
            """,
            "affected_files": """
                MATCH (n)-[:CALLS|EXTENDS*1..3]->(affected)
                WHERE n.id = $node_id OR n.path = $node_id
                MATCH (affected)<-[:CONTAINS]-(file:File)
                RETURN count(DISTINCT file) as count
            """
        }
        
        impact = {}
        with self.driver.session(database=neo4j_database) as session:
            for key, query in queries.items():
                try:
                    result = session.run(query, node_id=node_id)
                    record = result.single()
                    impact[key] = record["count"] if record else 0
                except Exception as e:
                    logger.error(f"Failed to run impact query {key}: {e}")
                    impact[key] = 0
        
        return impact
    
    def health_check(self) -> bool:
        """Check if graph store is healthy"""
        if not self.driver:
            return False
            
        try:
            # FIX: Use UPPERCASE attribute name
            neo4j_database = getattr(self.settings, 'NEO4J_DATABASE', 'neo4j')
            with self.driver.session(database=neo4j_database) as session:
                session.run("RETURN 1")
            return True
        except Exception as e:
            logger.error(f"Graph store health check failed: {e}")
            return False
    
    def close(self):
        """Close the driver connection"""
        if self.driver:
            self.driver.close()