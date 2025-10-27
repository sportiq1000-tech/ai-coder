"""
Documentation Generator Processor
"""
from typing import Dict, Any
from utils.logger import logger
from core.models.model_router import get_model_router, TaskType
from utils.prompts import get_documentation_prompt


class DocumentationGenerator:
    """Generates documentation for code"""
    
    def __init__(self):
        self.router = get_model_router()
        logger.info("DocumentationGenerator initialized")
    
    async def generate(
        self,
        code: str,
        language: str,
        include_examples: bool = True,
        format_type: str = "markdown"
    ) -> Dict[str, Any]:
        """
        Generate documentation for code
        
        Args:
            code: Code to document
            language: Programming language
            include_examples: Include usage examples
            format_type: Output format (markdown, docstring, html)
            
        Returns:
            Dictionary with documentation
        """
        logger.info(f"Generating {format_type} documentation for {language} code")
        
        # Generate prompt
        messages = get_documentation_prompt(
            code=code,
            language=language,
            include_examples=include_examples,
            format_type=format_type
        )
        
        # Route to model (using Azure Phi for documentation)
        response = await self.router.route(
            task_type=TaskType.DOCUMENTATION,
            messages=messages,
            temperature=0.5,
            max_tokens=3000
        )
        
        return {
            "documentation": response.content,
            "format": format_type,
            "language": language,
            "model_info": {
                "model": response.model,
                "provider": response.provider,
                "tokens_used": response.tokens_used
            }
        }