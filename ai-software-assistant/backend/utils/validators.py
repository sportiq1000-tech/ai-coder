"""
Input validation utilities
"""
from typing import Optional, Tuple
import re
from utils.exceptions import ValidationException
from utils.logger import logger


class CodeValidator:
    """Validates code inputs"""
    
    # Language-specific keywords for detection
    LANGUAGE_PATTERNS = {
        'python': [r'\bdef\b', r'\bclass\b', r'\bimport\b', r'\bif __name__\b'],
        'javascript': [r'\bfunction\b', r'\bconst\b', r'\blet\b', r'\bvar\b', r'=>'],
        'typescript': [r'\binterface\b', r'\btype\b', r': \w+', r'\bexport\b'],
        'java': [r'\bpublic class\b', r'\bprivate\b', r'\bstatic void\b'],
        'cpp': [r'#include', r'\bstd::\b', r'\bnamespace\b'],
        'go': [r'\bfunc\b', r'\bpackage\b', r':=', r'\bgo\b'],
        'rust': [r'\bfn\b', r'\blet mut\b', r'\bimpl\b', r'\bpub\b'],
    }
    
    # Security patterns to check
    SECURITY_PATTERNS = {
        'sql_injection': r'(SELECT|INSERT|UPDATE|DELETE).*FROM.*WHERE',
        'command_injection': r'(system|exec|eval|shell_exec)\s*\(',
        'path_traversal': r'\.\./|\.\.\\',
        'hardcoded_secrets': r'(password|secret|key|token)\s*=\s*["\'][^"\']{8,}["\']',
    }
    
    @staticmethod
    def validate_code_length(code: str, min_length: int = 1, max_length: int = 50000) -> bool:
        """Validate code length"""
        if not code or len(code.strip()) < min_length:
            raise ValidationException(f"Code must be at least {min_length} characters")
        
        if len(code) > max_length:
            raise ValidationException(f"Code exceeds maximum length of {max_length} characters")
        
        return True
    
    @staticmethod
    def detect_language(code: str) -> Optional[str]:
        """
        Auto-detect programming language from code
        Returns language name or None
        """
        code_lower = code.lower()
        scores = {}
        
        for lang, patterns in CodeValidator.LANGUAGE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    score += 1
            if score > 0:
                scores[lang] = score
        
        if scores:
            # Return language with highest score
            detected = max(scores, key=scores.get)
            logger.info(f"Detected language: {detected} (confidence: {scores[detected]})")
            return detected
        
        return None
    
    @staticmethod
    def check_security_issues(code: str) -> Tuple[bool, list]:
        """
        Check for potential security issues
        Returns (is_safe, issues_found)
        """
        issues = []
        
        for issue_type, pattern in CodeValidator.SECURITY_PATTERNS.items():
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                issues.append({
                    'type': issue_type,
                    'pattern': match.group(0),
                    'position': match.start()
                })
        
        is_safe = len(issues) == 0
        
        if not is_safe:
            logger.warning(f"Security issues detected: {len(issues)}")
        
        return is_safe, issues
    
    @staticmethod
    def sanitize_code(code: str) -> str:
        """
        Sanitize code input
        - Remove null bytes
        - Normalize line endings
        - Strip excessive whitespace
        """
        # Remove null bytes
        code = code.replace('\x00', '')
        
        # Normalize line endings
        code = code.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive blank lines (more than 2 consecutive)
        code = re.sub(r'\n{3,}', '\n\n', code)
        
        return code.strip()
    
    @staticmethod
    def validate_language(language: str, code: str) -> bool:
        """
        Validate that code matches declared language
        """
        detected = CodeValidator.detect_language(code)
        
        if detected and detected != language.lower():
            logger.warning(
                f"Language mismatch: declared={language}, detected={detected}"
            )
            # Don't raise error, just log warning
        
        return True


class RequestValidator:
    """Validates API requests"""
    
    @staticmethod
    def validate_description(description: str, min_length: int = 10, max_length: int = 5000) -> bool:
        """Validate description for code generation"""
        if not description or len(description.strip()) < min_length:
            raise ValidationException(
                f"Description must be at least {min_length} characters"
            )
        
        if len(description) > max_length:
            raise ValidationException(
                f"Description exceeds maximum length of {max_length} characters"
            )
        
        return True
    
    @staticmethod
    def validate_context(context: Optional[str], max_length: int = 10000) -> bool:
        """Validate context field"""
        if context and len(context) > max_length:
            raise ValidationException(
                f"Context exceeds maximum length of {max_length} characters"
            )
        return True