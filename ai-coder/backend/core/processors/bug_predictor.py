"""
Bug Prediction Processor
"""
from typing import Dict, Any
import json
from utils.logger import logger
from core.models.model_router import get_model_router, TaskType
from utils.prompts import get_bug_prediction_prompt


class BugPredictor:
    """Predicts potential bugs in code"""
    
    def __init__(self):
        self.router = get_model_router()
        logger.info("BugPredictor initialized")
    
    async def predict(
        self,
        code: str,
        language: str,
        context: str = None,
        severity_threshold: str = "medium"
    ) -> Dict[str, Any]:
        """
        Predict potential bugs in code
        
        Args:
            code: Code to analyze
            language: Programming language
            context: Additional context
            severity_threshold: Minimum severity to report
            
        Returns:
            Dictionary with bug predictions
        """
        logger.info(f"Predicting bugs in {language} code")
        
        # Generate prompt
        messages = get_bug_prediction_prompt(
            code=code,
            language=language,
            context=context,
            severity_threshold=severity_threshold
        )
        
        # Route to model
        response = await self.router.route(
            task_type=TaskType.BUG_PREDICTION,
            messages=messages,
            temperature=0.3,
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
            logger.error(f"Error parsing bug prediction response: {e}")
            return {
                "raw_response": response.content,
                "error": "Failed to parse structured response",
                "bugs": [],
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
            return {
                "raw_analysis": content,
                "bugs": [],
                "risk_score": None
            }