"""
Tests for Code Chunker implementation
"""

import pytest
from core.rag.chunker import CodeChunker
from schemas.rag_schemas import CodeChunk

class TestCodeChunker:
    """Test code chunking operations"""
    
    @pytest.fixture
    def chunker(self):
        """Create chunker instance for testing"""
        return CodeChunker()
    
    @pytest.mark.asyncio
    async def test_chunk_python_file(self, chunker):
        """Test chunking Python files"""
        python_code = '''
def hello_world():
    """Print hello world"""
    print("Hello, World!")

class Calculator:
    """Simple calculator class"""
    
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
'''
        
        chunks = await chunker.chunk_file("test.py", python_code, "python")
        
        assert len(chunks) >= 2  # At least function and class
        
        # Check function chunk
        func_chunk = next((c for c in chunks if c.metadata.get("name") == "hello_world"), None)
        assert func_chunk is not None
        assert func_chunk.chunk_type == "functiondef"
        assert func_chunk.start_line > 0
        
        # Check class chunk
        class_chunk = next((c for c in chunks if c.metadata.get("name") == "Calculator"), None)
        assert class_chunk is not None
        assert class_chunk.chunk_type == "classdef"
    
    @pytest.mark.asyncio
    async def test_chunk_javascript_file(self, chunker):
        """Test chunking JavaScript files"""
        js_code = '''
function greet(name) {
    return `Hello, ${name}!`;
}

class Person {
    constructor(name) {
        this.name = name;
    }
    
    sayHello() {
        return greet(this.name);
    }
}
'''
        
        chunks = await chunker.chunk_file("test.js", js_code, "javascript")
        
        assert len(chunks) >= 1  # At least some chunks
        
        # Verify chunks have proper metadata
        for chunk in chunks:
            assert chunk.file_path == "test.js"
            assert chunk.language == "javascript"
            assert chunk.start_line > 0
            assert chunk.end_line >= chunk.start_line
    
    @pytest.mark.asyncio
    async def test_chunk_generic_fallback(self, chunker):
        """Test generic chunking for unsupported languages"""
        generic_code = '\n'.join([f"Line {i}: Some code" for i in range(1, 200)])
        
        chunks = await chunker.chunk_file("test.xyz", generic_code, "unknown")
        
        assert len(chunks) >= 1  # Should create chunks
        
        # Verify generic chunks
        for chunk in chunks:
            assert chunk.chunk_type == "generic"
            assert chunk.metadata.get("chunking_method") == "generic"