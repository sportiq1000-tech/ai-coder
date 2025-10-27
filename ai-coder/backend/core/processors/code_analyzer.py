"""
Code Review Processor
"""
from typing import Dict, Any
import json
from utils.logger import logger
from core.models.model_router import get_model_router, TaskType
from utils.prompts import get_code_review_prompt
from utils.exceptions import ValidationException


class CodeAnalyzer:
    """Analyzes code and provides review feedback"""
    
    def __init__(self):
        self.router = get_model_router()
        logger.info("CodeAnalyzer initialized")
    
    async def analyze(
        self,
        code: str,
        language: str,
        context: str = None,
        check_style: bool = True,
        check_security: bool = True,
        check_performance: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze code and provide review
        
        Args:
            code: Code to review
            language: Programming language
            context: Additional context
            check_style: Check code style
            check_security: Check security issues
            check_performance: Check performance
            
        Returns:
            Dictionary with review results
        """
        logger.info(f"Analyzing {language} code ({len(code)} chars)")
        
        # Generate prompt
        messages = get_code_review_prompt(
            code=code,
            language=language,
            context=context,
            check_style=check_style,
            check_security=check_security,
            check_performance=check_performance
        )
        
        # Route to model
        response = await self.router.route(
            task_type=TaskType.CODE_REVIEW,
            messages=messages,
            temperature=0.3,  # Lower temperature for consistency
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
            logger.error(f"Error parsing review response: {e}")
            # Return raw response if parsing fails
            return {
                "raw_response": response.content,
                "error": "Failed to parse structured response",
                "model_info": {
                    "model": response.model,
                    "provider": response.provider
                }
            }
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse model response into structured format"""
        # Try to extract JSON from markdown code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # If not valid JSON, return as text analysis
            return {
                "summary": content[:500],
                "raw_analysis": content,
                "issues": [],
                "score": None
            }