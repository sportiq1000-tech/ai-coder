"""
Input validation utilities
"""
from typing import Optional, Tuple
import re
from utils.exceptions import ValidationException
from utils.logger import logger
from utils.security_monitor import security_monitor  # SECURITY FIX - Phase 2C: Add monitoring

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
# SECURITY FIX - Phase 2: Input Sanitization & Prompt Injection Protection
class InputSanitizer:
    """
    Sanitizes and validates inputs for security threats
    Detects: prompt injection, secret extraction, dangerous code patterns
    """
    
       # Patterns that might indicate prompt injection
    # SECURITY FIX - Phase 2B: Enhanced with 30+ patterns
    INJECTION_PATTERNS = [
        # Instruction Override Attempts
        r"ignore\s+previous\s+instructions",
        r"ignore\s+all\s+(previous\s+)?instructions",
        r"ignore\s+all\s+rules",
        r"disregard\s+all\s+prior",
        r"disregard\s+(previous\s+)?instructions",
        r"forget\s+everything",
        r"forget\s+all\s+(previous\s+)?instructions",
        r"override\s+previous\s+instructions",
        r"bypass\s+all",
        r"bypass\s+your\s+guidelines",
        
        # System Prompt Extraction
        r"system\s+prompt",
        r"reveal\s+your\s+instructions",
        r"show\s+me\s+your\s+prompt",
        r"what\s+are\s+your\s+rules",
        r"what\s+are\s+your\s+instructions",
        r"show\s+your\s+system\s+message",
        r"print\s+your\s+instructions",
        r"output\s+your\s+prompt",
        
        # Role/Behavior Manipulation
        r"pretend\s+you\s+are",
        r"act\s+as\s+if",
        r"act\s+as\s+a",
        r"roleplay\s+as",
        r"you\s+are\s+now",
        r"simulate\s+being",
        r"behave\s+like",
        
        # Instruction Injection
        r"new\s+instructions:",
        r"updated\s+instructions:",
        r"additional\s+instructions:",
        r"new\s+rules:",
        
        # Special Characters/Tokens (Model-specific)
        r"</system>",
        r"<system>",
        r"```system",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"<\|endoftext\|>",
        
        # Jailbreak Attempts
        r"jailbreak",
        r"DAN\s+mode",  # "Do Anything Now"
        r"developer\s+mode",
        
        # Malicious Intent Keywords
        r"hack\s+into",
        r"hack\s+the",
        r"exploit\s+",
        r"crack\s+",
        r"break\s+into",
        
        # Context Switching
        r"switch\s+to",
        r"change\s+to",
        r"enter\s+.*\s+mode",
         # SECURITY FIX - Phase 2C: Grandma Technique Detection
        # Narrative Framing Attacks
        r"my\s+grandmother\s+(used\s+to|would)",
        r"my\s+grandma\s+(used\s+to|would)",
        r"deceased\s+(grandmother|grandma|relative)",
        r"before\s+(she|he)\s+(died|passed\s+away)",
        r"bedtime\s+stor(y|ies)",
        
        # Roleplay Via Proxy
        r"help\s+me\s+remember\s+what.*said",
        r"tell\s+me\s+what.*used\s+to\s+say",
        r"complete.*last\s+wish",
        
        # Creative Writing Exploits
        r"(writing|write)\s+(a\s+)?(novel|story|book).*where",
        r"for\s+my\s+(school\s+)?project",
        r"academic\s+research\s+(about|on)",
        r"hypothetical\s+scenario",
        r"thought\s+experiment",
        
        # Character Roleplay
        r"roleplay\s+as\s+.*\s+who",
        r"dialogue\s+where",
        r"character.*says",
        r"imagine\s+you.*who\s+(worked|knows)",
    ]
    
        # Patterns that might be trying to extract secrets
    # SECURITY FIX - Phase 2B: Enhanced secret detection
    SECRET_EXTRACTION_PATTERNS = [
        # Direct Key/Token References
        r"(api[_\s\-]?key)",
        r"(access[_\s\-]?token)",
        r"(secret[_\s\-]?key)",
        r"(auth[_\s\-]?token)",
        r"(bearer[_\s\-]?token)",
        r"password",
        r"passwd",
        r"credentials",
        
        # Environment Variable Access
        r"environment\s+variable",
        r"process\.env",
        r"os\.environ",
        r"getenv",
        r"env\s*\[",
        r"\$\{.*\}",  # Shell variable expansion
        
        # Configuration Extraction
        r"show\s+me\s+.*\s+config",
        r"reveal\s+.*\s+settings",
        r"print\s+.*\s+env",
        r"display\s+.*\s+config",
        r"output\s+.*\s+settings",
        r"list\s+.*\s+env",
        r"dump\s+.*\s+config",
        
        # File Path Attempts
        r"\.env\s*file",
        r"config\.json",
        r"secrets\.yaml",
        r"\.aws/credentials",
        
        # Cloud Provider Secrets
        r"AWS_SECRET",
        r"AZURE_KEY",
        r"GCP_KEY",
        r"OPENAI_API_KEY",
        r"GROQ_API_KEY",
    ]
    
        # Dangerous code patterns (beyond what CodeValidator checks)
    # SECURITY FIX - Phase 2B: Enhanced dangerous code detection
    DANGEROUS_PATTERNS = {
        'python': [
            # Dynamic Code Execution
            r"__import__\s*\(",
            r"compile\s*\(",
            r"exec\s*\(",
            r"eval\s*\(",
            
            # Introspection (can reveal system info)
            r"globals\s*\(\)",
            r"locals\s*\(\)",
            r"vars\s*\(\)",
            r"dir\s*\(\)",
            r"__dict__",
            r"__class__",
            r"__bases__",
            
            # File System Access
            r"open\s*\(",
            r"file\s*\(",
            r"read\s*\(",
            r"write\s*\(",
            
            # Network/System Access
            r"socket\.",
            r"requests\.",
            r"urllib\.",
            r"subprocess\.",
            r"os\.system",
            r"os\.popen",
            
            # Pickle (can execute arbitrary code)
            r"pickle\.",
            r"cPickle\.",
            r"_pickle\.",
        ],
    }
    
    def __init__(self):
        # Compile patterns for efficiency
        self.injection_regex = re.compile(
            '|'.join(self.INJECTION_PATTERNS), 
            re.IGNORECASE
        )
        self.secret_regex = re.compile(
            '|'.join(self.SECRET_EXTRACTION_PATTERNS), 
            re.IGNORECASE
        )
    
    def check_prompt_injection(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check for prompt injection attempts
        Returns (is_suspicious, matched_pattern)
        """
        match = self.injection_regex.search(text)
        if match:
            logger.warning(f"Prompt injection attempt detected: {match.group()}")
            return True, match.group()
        return False, None
    
    def check_secret_extraction(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check for attempts to extract secrets
        Returns (is_suspicious, matched_pattern)
        """
        match = self.secret_regex.search(text)
        if match:
            logger.warning(f"Secret extraction attempt detected: {match.group()}")
            return True, match.group()
        return False, None
    
    def check_dangerous_code(self, code: str, language: str) -> Tuple[bool, list]:
        """
        Check for dangerous code patterns beyond basic security
        Returns (is_dangerous, patterns_found)
        """
        patterns = self.DANGEROUS_PATTERNS.get(language.lower(), [])
        found = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                found.append(match.group())
        
        if found:
            logger.warning(f"Dangerous patterns in {language}: {found}")
        
        return len(found) > 0, found
    
    def sanitize_input(self, text: str) -> str:
        """
        Sanitize input text
        - Remove null bytes
        - Normalize whitespace
        - Remove control characters
        """
        if not text:
            return text
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove other control characters except newlines and tabs
        text = ''.join(
            char for char in text 
            if char in ['\n', '\t'] or 
            (ord(char) >= 32 and ord(char) <= 126) or 
            ord(char) > 127  # Allow unicode
        )
        
        return text
    
    def validate_code_input(
        self, 
        code: str, 
        language: str,
        check_injection: bool = True,
        check_secrets: bool = True
    ) -> Tuple[bool, str]:
        """
        Complete validation of code input
        Returns (is_valid, sanitized_code_or_error_message)
        """
        from utils.config import settings
        
        # Check for prompt injection if enabled
        if check_injection and settings.ENABLE_PROMPT_INJECTION_CHECK:
            is_injection, pattern = self.check_prompt_injection(code)
            if is_injection:
                # SECURITY FIX - Phase 2C: This will be logged by the route handler
                return False, f"prompt_injection|||{pattern}|||Suspicious input detected: potential prompt injection"
        
        # Check for secret extraction if enabled
        if check_secrets and settings.ENABLE_SECRET_DETECTION:
            is_secret, pattern = self.check_secret_extraction(code)
            if is_secret:
                # SECURITY FIX - Phase 2C: This will be logged by the route handler
                return False, f"secret_extraction|||{pattern}|||Suspicious input detected: potential secret extraction"
        
        # Check for dangerous patterns (log but don't block)
        is_dangerous, patterns = self.check_dangerous_code(code, language)
        if is_dangerous:
            logger.warning(f"Dangerous patterns found but allowing: {patterns}")
        
        # Sanitize the input
        sanitized = self.sanitize_input(code)
        
        return True, sanitized

# SECURITY FIX - Phase 2: Global sanitizer instance
sanitizer = InputSanitizer()