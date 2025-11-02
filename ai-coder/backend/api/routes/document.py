"""
Documentation Generation API endpoint with caching and validation
"""
from fastapi import APIRouter, HTTPException, Request
from schemas.request_schemas import DocumentationRequest
from schemas.response_schemas import APIResponse, ResponseStatus, ModelInfo
from core.processors.documentation_generator import DocumentationGenerator
from utils.logger import logger
from utils.exceptions import AIAssistantException, ValidationException
from utils.validators import CodeValidator, sanitizer
from utils.cache import get_cache, Cache
from utils.metrics import get_metrics
from utils.config import settings
import time
import uuid

router = APIRouter()
doc_generator = DocumentationGenerator()


@router.post("/document", response_model=APIResponse)
async def generate_documentation(req: DocumentationRequest, request: Request):
    """
    Generate documentation for code with caching
    
    - **code**: Code to document (required)
    - **language**: Programming language
    - **include_examples**: Include usage examples (default: true)
    - **format**: Output format - markdown, docstring, or html (default: markdown)
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    cache = get_cache()
    metrics = get_metrics()
    
    logger.info(f"Documentation request {request_id}: {req.language} -> {req.format}")
    
    try:
        # VALIDATION
        CodeValidator.validate_code_length(
            req.code,
            min_length=settings.MIN_CODE_LENGTH,
            max_length=settings.MAX_CODE_LENGTH
        )
        
        sanitized_code = CodeValidator.sanitize_code(req.code)
        
        # SECURITY FIX - Phase 2: Validate input
        is_valid, validation_result = sanitizer.validate_code_input(
            sanitized_code,
            req.language.value,
            check_injection=settings.ENABLE_PROMPT_INJECTION_CHECK,
            check_secrets=settings.ENABLE_SECRET_DETECTION
        )
        if not is_valid:
            logger.warning(f"Input validation failed for {request_id}: {validation_result}")
            raise ValidationException(validation_result)
        
        sanitized_code = validation_result
        
        # CHECK CACHE (longer TTL for docs)
        if settings.CACHE_ENABLED:
            cache_key = f"document:{Cache.generate_key(sanitized_code, req.language, req.format, req.include_examples)}"
            cached_result = await cache.get(cache_key)
            
            if cached_result:
                logger.info(f"Cache hit for documentation {request_id}")
                processing_time = (time.time() - start_time) * 1000
                
                metrics.log_request(
                    endpoint="/api/document",
                    task_type="documentation",
                    model_used="cached",
                    provider="cache",
                    tokens_used=0,
                    processing_time_ms=processing_time,
                    status="success_cached"
                )
                
                return APIResponse(
                    status=ResponseStatus.SUCCESS,
                    message="Documentation generated (cached)",
                    data=cached_result.get("data"),
                    model_info=ModelInfo(**cached_result.get("model_info", {})),
                    request_id=request_id
                )
        
        # PROCESS REQUEST
        result = await doc_generator.generate(
            code=sanitized_code,
            language=req.language.value,
            include_examples=req.include_examples,
            format_type=req.format
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        model_info_data = result.pop("model_info", {})
        model_info = ModelInfo(
            model_name=model_info_data.get("model", "unknown"),
            provider=model_info_data.get("provider", "unknown"),
            tokens_used=model_info_data.get("tokens_used"),
            processing_time_ms=processing_time
        )
        
        # CACHE RESULT (24 hours for docs)
        if settings.CACHE_ENABLED:
            await cache.set(
                cache_key,
                {
                    "data": result,
                    "model_info": model_info.dict()
                },
                ttl=settings.CACHE_TTL_DOCUMENTATION
            )
        
        # LOG METRICS
        metrics.log_request(
            endpoint="/api/document",
            task_type="documentation",
            model_used=model_info.model_name,
            provider=model_info.provider,
            tokens_used=model_info.tokens_used or 0,
            processing_time_ms=processing_time,
            status="success"
        )
        
        logger.info(f"Documentation generated: {request_id} ({processing_time:.2f}ms)")
        
        return APIResponse(
            status=ResponseStatus.SUCCESS,
            message="Documentation generated successfully",
            data=result,
            model_info=model_info,
            request_id=request_id
        )
        
    except ValidationException as e:
        logger.error(f"Validation failed {request_id}: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
        
    except AIAssistantException as e:
        logger.error(f"Documentation generation failed {request_id}: {e.message}")
        metrics.log_request(
            endpoint="/api/document",
            task_type="documentation",
            model_used="unknown",
            provider="unknown",
            tokens_used=0,
            processing_time_ms=(time.time() - start_time) * 1000,
            status="error",
            error=e.message
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)
        
    except Exception as e:
        logger.exception(f"Unexpected error in documentation generation {request_id}")
        raise HTTPException(status_code=500, detail=str(e))