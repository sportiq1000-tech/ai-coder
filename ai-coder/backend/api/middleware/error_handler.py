"""
Global error handling middleware
SECURITY FIX - Phase 2: Secure error responses with error ID tracking
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from utils.exceptions import AIAssistantException
from utils.logger import logger
from utils.config import settings
from schemas.response_schemas import ErrorResponse, ResponseStatus
from datetime import datetime
import uuid
import traceback


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handler with security-focused error responses
    - Hides stack traces in production
    - Generates error IDs for tracking
    - Logs detailed errors server-side
    - Returns generic messages to users
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique error ID for this request
        request_id = str(uuid.uuid4())
        
        try:
            response = await call_next(request)
            return response
            
        except AIAssistantException as e:
            # Application-specific errors (expected)
            logger.error(
                f"Application error [{request_id}]: {e.message}",
                extra={
                    "error_id": request_id,
                    "error_type": e.__class__.__name__,
                    "path": request.url.path
                }
            )
            
            error_response = ErrorResponse(
                status=ResponseStatus.ERROR,
                message=e.message,
                error_code=e.__class__.__name__,
                timestamp=datetime.utcnow()
            )
            
            # SECURITY FIX: Add error ID but don't expose internal details
            response_dict = error_response.dict()
            response_dict["error_id"] = request_id
            
            return JSONResponse(
                status_code=e.status_code,
                content=response_dict
            )
            
        except Exception as e:
            # Unexpected errors (should be investigated)
            # SECURITY FIX: Log full details but hide from user
            logger.exception(
                f"Unexpected error [{request_id}]: {str(e)}",
                extra={
                    "error_id": request_id,
                    "path": request.url.path,
                    "method": request.method
                }
            )
            
            # SECURITY FIX: Different responses for dev vs production
            if settings.DEBUG:
                # Development: Show error details
                error_response = ErrorResponse(
                    status=ResponseStatus.ERROR,
                    message="An unexpected error occurred",
                    error_code="InternalServerError",
                    details={
                        "error": str(e),
                        "type": e.__class__.__name__,
                        "error_id": request_id
                    },
                    timestamp=datetime.utcnow()
                )
            else:
                # Production: Hide all details
                error_response = ErrorResponse(
                    status=ResponseStatus.ERROR,
                    message="An internal error occurred. Please contact support with the error ID.",
                    error_code="InternalServerError",
                    details={"error_id": request_id},  # Only include error ID
                    timestamp=datetime.utcnow()
                )
            
            return JSONResponse(
                status_code=500,
                content=error_response.dict()
            )