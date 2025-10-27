"""
Global error handling middleware
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from utils.exceptions import AIAssistantException
from utils.logger import logger
from utils.config import settings
from schemas.response_schemas import ErrorResponse, ResponseStatus
from datetime import datetime


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handler"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except AIAssistantException as e:
            logger.error(f"Application error: {e.message}")
            error_response = ErrorResponse(
                status=ResponseStatus.ERROR,
                message=e.message,
                error_code=e.__class__.__name__,
                timestamp=datetime.utcnow()
            )
            return JSONResponse(
                status_code=e.status_code,
                content=error_response.dict()
            )
        except Exception as e:
            logger.exception(f"Unexpected error: {str(e)}")
            error_response = ErrorResponse(
                status=ResponseStatus.ERROR,
                message="An unexpected error occurred",
                error_code="InternalServerError",
                details={"error": str(e)} if settings.DEBUG else None,
                timestamp=datetime.utcnow()
            )
            return JSONResponse(
                status_code=500,
                content=error_response.dict()
            )