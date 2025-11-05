"""
Document Chunking Strategy
Intelligently splits code files into meaningful chunks
"""

from typing import List, Dict, Any, Optional
import ast
import re
from pathlib import Path
from utils.logger import logger
from schemas.rag_schemas import CodeChunk

class CodeChunker:
    """
    Splits code files into semantic chunks based on language and structure
    """
    
    def __init__(self):
        """Initialize the chunker with default settings"""
        self.chunk_size = 1000  # Target chunk size in characters
        self.chunk_overlap = 200  # Overlap between chunks
        self.language_parsers = {
            "python": self._chunk_python,
            "javascript": self._chunk_javascript,
            "typescript": self._chunk_typescript,
            "java": self._chunk_java,
            "cpp": self._chunk_cpp,
            "c++": self._chunk_cpp,
            "csharp": self._chunk_csharp,
            "c#": self._chunk_csharp
        }
    
    async def chunk_file(
        self, 
        file_path: str, 
        content: str, 
        language: str
    ) -> List[CodeChunk]:
        """
        Chunk a code file into semantic pieces
        
        Args:
            file_path: Path to the file
            content: File content
            language: Programming language
            
        Returns:
            List of code chunks
        """
        logger.info(f"Chunking file: {file_path} ({language})")
        
        # Get appropriate parser for language
        parser = self.language_parsers.get(
            language.lower(), 
            self._chunk_generic
        )
        
        # Parse the file
        chunks = parser(content, file_path, language)
        
        # Post-process chunks
        chunks = self._post_process_chunks(chunks)
        
        logger.info(f"Created {len(chunks)} chunks for {file_path}")
        
        return chunks
    
    def _chunk_python(
        self, 
        content: str, 
        file_path: str, 
        language: str
    ) -> List[CodeChunk]:
        """Chunk Python code using AST parsing"""
        try:
            tree = ast.parse(content)
            chunks = []
            lines = content.split('\n')
            
            # Extract top-level functions and classes
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    start_line = node.lineno
                    end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                    
                    # Extract the code
                    chunk_content = '\n'.join(lines[start_line-1:end_line])
                    
                    # Extract metadata
                    metadata = self._extract_python_metadata(node, chunk_content)
                    
                    chunk = CodeChunk(
                        id=f"{file_path}:{start_line}-{end_line}",
                        content=chunk_content,
                        file_path=file_path,
                        language=language,
                        chunk_type=node.__class__.__name__.lower(),
                        start_line=start_line,
                        end_line=end_line,
                        metadata=metadata
                    )
                    chunks.append(chunk)
            
            # If no top-level constructs found, use generic chunking
            if not chunks:
                return self._chunk_generic(content, file_path, language)
            
            return chunks
            
        except SyntaxError as e:
            # Fall back to generic chunking for invalid Python
            logger.warning(f"Invalid Python syntax in {file_path}, using generic chunking: {e}")
            return self._chunk_generic(content, file_path, language)
    
    def _chunk_javascript(
        self, 
        content: str, 
        file_path: str, 
        language: str
    ) -> List[CodeChunk]:
        """Chunk JavaScript code using regex patterns"""
        chunks = []
        
        # Function patterns
        function_patterns = [
            r'(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*{',
            r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>\s*{',
            r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\s*\([^)]*\)\s*{',
            r'(\w+)\s*:\s*(?:async\s+)?function\s*\([^)]*\)\s*{',
            r'class\s+(\w+)(?:\s+extends\s+\w+)?\s*{'
        ]
        
        lines = content.split('\n')
        
        for pattern in function_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            
            for match in matches:
                func_name = match.group(1)
                start_pos = match.start()
                
                # Find the end of the function/class
                end_pos = self._find_brace_end(content, start_pos)
                
                if end_pos > start_pos:
                    # Convert positions to line numbers
                    start_line = content[:start_pos].count('\n') + 1
                    end_line = content[:end_pos].count('\n') + 1
                    
                    chunk_content = '\n'.join(lines[start_line-1:end_line])
                    
                    metadata = {
                        "name": func_name,
                        "type": "function" if "function" in pattern else "class"
                    }
                    
                    chunk = CodeChunk(
                        id=f"{file_path}:{start_line}-{end_line}",
                        content=chunk_content,
                        file_path=file_path,
                        language=language,
                        chunk_type=metadata["type"],
                        start_line=start_line,
                        end_line=end_line,
                        metadata=metadata
                    )
                    chunks.append(chunk)
        
        # If no structured chunks found, use generic chunking
        if not chunks:
            return self._chunk_generic(content, file_path, language)
        
        return chunks
    
    def _chunk_typescript(
        self, 
        content: str, 
        file_path: str, 
        language: str
    ) -> List[CodeChunk]:
        """Chunk TypeScript code (similar to JavaScript)"""
        return self._chunk_javascript(content, file_path, language)
    
    def _chunk_java(
        self, 
        content: str, 
        file_path: str, 
        language: str
    ) -> List[CodeChunk]:
        """Chunk Java code using regex patterns"""
        chunks = []
        
        # Class and method patterns
        class_pattern = r'(?:public\s+|private\s+|protected\s+)?(?:abstract\s+|final\s+)?(class|interface|enum)\s+(\w+)'
        
        lines = content.split('\n')
        
        # Find classes
        class_matches = list(re.finditer(class_pattern, content, re.MULTILINE))
        
        for class_match in class_matches:
            class_type = class_match.group(1)
            class_name = class_match.group(2)
            class_start = class_match.start()
            
            # Find the end of the class
            class_end = self._find_brace_end(content, class_start)
            
            if class_end > class_start:
                # Create class chunk
                class_start_line = content[:class_start].count('\n') + 1
                class_end_line = content[:class_end].count('\n') + 1
                
                class_chunk = CodeChunk(
                    id=f"{file_path}:class:{class_name}",
                    content='\n'.join(lines[class_start_line-1:class_end_line]),
                    file_path=file_path,
                    language=language,
                    chunk_type=class_type,
                    start_line=class_start_line,
                    end_line=class_end_line,
                    metadata={"name": class_name, "type": class_type}
                )
                chunks.append(class_chunk)
        
        # If no structured chunks found, use generic chunking
        if not chunks:
            return self._chunk_generic(content, file_path, language)
        
        return chunks
    
    def _chunk_cpp(
        self, 
        content: str, 
        file_path: str, 
        language: str
    ) -> List[CodeChunk]:
        """Chunk C++ code using regex patterns"""
        chunks = []
        
        # Function and class patterns
        patterns = [
            r'(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*(?:const\s+)?{',  # Functions
            r'(?:class|struct)\s+(\w+)(?:\s*:\s*[\w\s,]+)?\s*{',  # Classes/structs
        ]
        
        lines = content.split('\n')
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            
            for match in matches:
                name = match.group(1)
                start_pos = match.start()
                end_pos = self._find_brace_end(content, start_pos)
                
                if end_pos > start_pos:
                    start_line = content[:start_pos].count('\n') + 1
                    end_line = content[:end_pos].count('\n') + 1
                    
                    chunk_content = '\n'.join(lines[start_line-1:end_line])
                    
                    chunk = CodeChunk(
                        id=f"{file_path}:{start_line}-{end_line}",
                        content=chunk_content,
                        file_path=file_path,
                        language=language,
                        chunk_type="function_or_class",
                        start_line=start_line,
                        end_line=end_line,
                        metadata={"name": name}
                    )
                    chunks.append(chunk)
        
        if not chunks:
            return self._chunk_generic(content, file_path, language)
        
        return chunks
    
    def _chunk_csharp(
        self, 
        content: str, 
        file_path: str, 
        language: str
    ) -> List[CodeChunk]:
        """Chunk C# code (similar to Java)"""
        return self._chunk_java(content, file_path, language)
    
    def _chunk_generic(
        self, 
        content: str, 
        file_path: str, 
        language: str
    ) -> List[CodeChunk]:
        """Generic chunking for unsupported languages or fallback"""
        chunks = []
        lines = content.split('\n')
        
        # Create overlapping chunks
        chunk_size_lines = 50  # Number of lines per chunk
        overlap_lines = 10
        
        for i in range(0, len(lines), chunk_size_lines - overlap_lines):
            chunk_lines = lines[i:i + chunk_size_lines]
            
            if not chunk_lines or not ''.join(chunk_lines).strip():
                continue
            
            chunk_content = '\n'.join(chunk_lines)
            start_line = i + 1
            end_line = i + len(chunk_lines)
            
            chunk = CodeChunk(
                id=f"{file_path}:{start_line}-{end_line}",
                content=chunk_content,
                file_path=file_path,
                language=language,
                chunk_type="generic",
                start_line=start_line,
                end_line=end_line,
                metadata={"chunking_method": "generic"}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _extract_python_metadata(
        self, 
        node: ast.AST, 
        content: str
    ) -> Dict[str, Any]:
        """Extract metadata from Python AST node"""
        metadata = {}
        
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            metadata.update({
                "name": node.name,
                "type": "function",
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "args": [arg.arg for arg in node.args.args],
                "returns": ast.unparse(node.returns) if node.returns else None,
                "decorators": [ast.unparse(dec) for dec in node.decorator_list],
                "docstring": ast.get_docstring(node) or None
            })
            
            # Calculate complexity (simplified)
            complexity = 1
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                    complexity += 1
            metadata["complexity"] = complexity
            
        elif isinstance(node, ast.ClassDef):
            metadata.update({
                "name": node.name,
                "type": "class",
                "bases": [ast.unparse(base) for base in node.bases],
                "decorators": [ast.unparse(dec) for dec in node.decorator_list],
                "docstring": ast.get_docstring(node) or None
            })
        
        return metadata
    
    def _find_brace_end(self, content: str, start_pos: int) -> int:
        """Find the position of the closing brace"""
        brace_count = 0
        in_string = False
        string_char = None
        escape_next = False
        
        for i in range(start_pos, len(content)):
            char = content[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char in ('"', "'"):
                if not in_string:
                    in_string = True
                    string_char = char
                elif in_string and char == string_char:
                    in_string = False
                    string_char = None
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return i + 1
        
        return len(content)
    
    def _post_process_chunks(self, chunks: List[CodeChunk]) -> List[CodeChunk]:
        """Post-process chunks to ensure quality"""
        processed_chunks = []
        
        for chunk in chunks:
            # Skip empty chunks
            if not chunk.content.strip():
                continue
            
            # Skip very small chunks (likely noise)
            if len(chunk.content) < 50:
                continue
            
            # Ensure chunk has required fields
            if not chunk.id:
                chunk.id = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
            
            if not chunk.metadata:
                chunk.metadata = {}
            
            processed_chunks.append(chunk)
        
        return processed_chunks