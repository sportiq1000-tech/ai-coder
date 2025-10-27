"""
Custom exception classes for the application
"""

class AIAssistantException(Exception):
    """Base exception for all custom exceptions"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ModelException(AIAssistantException):
    """Exception raised for model-related errors"""
    def __init__(self, message: str, model_name: str = None):
        self.model_name = model_name
        super().__init__(message, status_code=502)


class RateLimitException(AIAssistantException):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)


class ValidationException(AIAssistantException):
    """Exception raised for validation errors"""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class AuthenticationException(AIAssistantException):
    """Exception raised for authentication errors"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class NotFoundException(AIAssistantException):
    """Exception raised when resource is not found"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ServiceUnavailableException(AIAssistantException):
    """Exception raised when service is unavailable"""
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message, status_code=503)