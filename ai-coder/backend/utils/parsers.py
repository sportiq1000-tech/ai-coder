"""
Response parsing utilities
"""
import json
import re
from typing import Dict, Any, Optional
from utils.logger import logger


class ResponseParser:
    """Parse and normalize model responses"""
    
    @staticmethod
    def extract_json(content: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from model response
        Handles markdown code blocks and malformed JSON
        """
        # Try direct JSON parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to extract from markdown code block
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                try:
                    return json.loads(content[start:end].strip())
                except json.JSONDecodeError:
                    pass
        
        # Try to find JSON object in content
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        logger.warning("Could not extract valid JSON from response")
        return None
    
    @staticmethod
    def extract_code(content: str, language: Optional[str] = None) -> str:
        """
        Extract code from markdown code blocks
        """
        # Try language-specific code block
        if language:
            pattern = f"```{language}\\n([\\s\\S]*?)```"
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Try generic code block
        pattern = r"```[\w]*\n([\s\S]*?)```"
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()
        
        # No code block found, return as-is
        return content.strip()
    
    @staticmethod
    def normalize_code_review(response: str) -> Dict[str, Any]:
        """Normalize code review response"""
        json_data = ResponseParser.extract_json(response)
        
        if json_data:
            # Ensure required fields
            return {
                'summary': json_data.get('summary', 'Code review completed'),
                'issues': json_data.get('issues', []),
                'score': json_data.get('score'),
                'recommendations': json_data.get('recommendations', []),
                'raw_response': response
            }
        
        # Fallback: return as text
        return {
            'summary': response[:500],
            'raw_analysis': response,
            'issues': [],
            'score': None
        }
    
    @staticmethod
    def normalize_bug_prediction(response: str) -> Dict[str, Any]:
        """Normalize bug prediction response"""
        json_data = ResponseParser.extract_json(response)
        
        if json_data:
            return {
                'bugs': json_data.get('bugs', []),
                'risk_score': json_data.get('risk_score'),
                'overall_assessment': json_data.get('overall_assessment', ''),
                'raw_response': response
            }
        
        return {
            'raw_analysis': response,
            'bugs': [],
            'risk_score': None
        }
    
    @staticmethod
    def normalize_code_generation(response: str, language: str) -> Dict[str, Any]:
        """Normalize code generation response"""
        json_data = ResponseParser.extract_json(response)
        
        if json_data and 'code' in json_data:
            # Nested JSON in code field fix
            code = json_data.get('code', '')
            if isinstance(code, str) and code.strip().startswith('{'):
                try:
                    code_json = json.loads(code)
                    code = code_json.get('code', code)
                except:
                    pass
            
            return {
                'code': ResponseParser.extract_code(code, language),
                'explanation': json_data.get('explanation', ''),
                'complexity': json_data.get('complexity', ''),
                'dependencies': json_data.get('dependencies', []),
                'usage_example': json_data.get('usage_example', ''),
                'raw_response': response
            }
        
        # Try to extract code without JSON structure
        code = ResponseParser.extract_code(response, language)
        return {
            'code': code,
            'explanation': 'Code extracted from response',
            'raw_response': response
        }