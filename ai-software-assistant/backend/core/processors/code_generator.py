"""
Code Generation Processor
"""
from typing import Dict, Any
import json
from utils.logger import logger
from core.models.model_router import get_model_router, TaskType
from utils.prompts import get_code_generation_prompt


class CodeGenerator:
    """Generates code from natural language descriptions"""
    
    def __init__(self):
        self.router = get_model_router()
        logger.info("CodeGenerator initialized")
    
    async def generate(
        self,
        description: str,
        language: str,
        context: str = None,
        include_tests: bool = False
    ) -> Dict[str, Any]:
        """
        Generate code from description
        
        Args:
            description: Natural language description
            language: Target programming language
            context: Additional context
            include_tests: Include unit tests
            
        Returns:
            Dictionary with generated code
        """
        logger.info(f"Generating {language} code from description")
        
        # Generate prompt
        messages = get_code_generation_prompt(
            description=description,
            language=language,
            context=context,
            include_tests=include_tests
        )
        
        # Route to model (using Cerebras for code generation)
        response = await self.router.route(
            task_type=TaskType.CODE_GENERATION,
            messages=messages,
            temperature=0.7,
            max_tokens=4096
        )
        
        # Parse response
        try:
            result = self._parse_response(response.content)
            result["model_info"] = {
                "model": response.model,
                "provider": response.provider,
                "tokens_used": response.tokens_used
            }
            return result
        except Exception as e:
            logger.error(f"Error parsing generation response: {e}")
            return {
                "code": response.content,
                "explanation": "Raw generated content",
                "model_info": {
                    "model": response.model,
                    "provider": response.provider
                }
            }
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse model response into structured format"""
        # Try to extract JSON
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            json_content = content[start:end].strip()
            try:
                return json.loads(json_content)
            except:
                pass
        
        # If not JSON, try to extract code blocks
        if "```" in content:
            # Extract first code block as the generated code
            start = content.find("```")
            # Skip language identifier if present
            newline = content.find("\n", start)
            end = content.find("```", newline)
            code = content[newline+1:end].strip() if end > newline else content
            
            return {
                "code": code,
                "explanation": "Code extracted from response",
                "raw_response": content
            }
        
        # Return as-is if no structure found
        return {
            "code": content,
            "explanation": "Unstructured response"
        }