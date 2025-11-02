"""
Code Review API endpoint with caching, validation, and metrics
"""
from fastapi import APIRouter, HTTPException, Request
from schemas.request_schemas import CodeReviewRequest
from schemas.response_schemas import APIResponse, ResponseStatus, ModelInfo
from core.processors.code_analyzer import CodeAnalyzer
from utils.logger import logger
from utils.exceptions import AIAssistantException, ValidationException
from utils.validators import CodeValidator, sanitizer
from utils.parsers import ResponseParser
from utils.cache import get_cache, RedisCache
from utils.metrics import get_metrics
from utils.config import settings
import time
import uuid
from utils.security_monitor import security_monitor

router = APIRouter()
analyzer = CodeAnalyzer()


@router.post("/review", response_model=APIResponse)
async def review_code(req: CodeReviewRequest, request: Request):  # Add request parameter
    """
    Review code and provide suggestions with caching and validation
    
    - **code**: Code to review (required)
    - **language**: Programming language
    - **context**: Additional context (optional)
    - **check_style**: Check code style (default: true)
    - **check_security**: Check security (default: true)
    - **check_performance**: Check performance (default: true)
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    cache = get_cache()
    metrics = get_metrics()
    
    logger.info(f"Code review request {request_id}: {req.language}")
    
    try:
        # 1. VALIDATION
        logger.info(f"Validating input for {request_id}")
        
        # Validate code length
        CodeValidator.validate_code_length(
            req.code,
            min_length=settings.MIN_CODE_LENGTH,
            max_length=settings.MAX_CODE_LENGTH
        )
        
        # Sanitize code
        sanitized_code = CodeValidator.sanitize_code(req.code)
        
        
                # SECURITY FIX - Phase 2: Check for prompt injection and secret extraction
        is_valid, validation_result = sanitizer.validate_code_input(
            sanitized_code,
            req.language.value,
            check_injection=settings.ENABLE_PROMPT_INJECTION_CHECK,
            check_secrets=settings.ENABLE_SECRET_DETECTION
        )
        if not is_valid:
            # SECURITY FIX - Phase 2C: Parse validation result for monitoring
            # Format: "attack_type|||pattern|||message"
            parts = validation_result.split("|||")
            if len(parts) == 3:
                attack_type, matched_pattern, error_msg = parts
            else:
                attack_type, matched_pattern, error_msg = "validation_error", None, validation_result
            
            # Log the security block
            security_monitor.log_blocked_request(
                request_id=request_id,
                endpoint="/api/review",
                client_ip=request.client.host if hasattr(request, 'client') else "unknown",
                api_key_user="authenticated",  # We know they're auth'd if they got here
                input_data=sanitized_code,
                block_reason=error_msg,
                matched_pattern=matched_pattern,
                attack_type=attack_type
            )
            
            logger.warning(f"Input validation failed for {request_id}: {error_msg}")
            raise ValidationException(error_msg)
        
        # Use the sanitized result from validator
        sanitized_code = validation_result
     
        # Auto-detect language if needed
        if settings.AUTO_DETECT_LANGUAGE:
            detected = CodeValidator.detect_language(sanitized_code)
            if detected and detected != req.language.value:
                logger.warning(
                    f"Language mismatch: declared={req.language}, detected={detected}"
                )
        
        # Security check
        if settings.VALIDATE_CODE_SECURITY:
            is_safe, security_issues = CodeValidator.check_security_issues(sanitized_code)
            if not is_safe:
                logger.warning(f"Security issues detected: {len(security_issues)}")
        
        # 2. CHECK CACHE
        if settings.CACHE_ENABLED:
            cache_key = f"review:{RedisCache.generate_key(sanitized_code, req.language, req.check_style, req.check_security, req.check_performance)}"
            cached_result = await cache.get(cache_key)
            
            if cached_result:
                logger.info(f"Cache hit for review {request_id}")
                processing_time = (time.time() - start_time) * 1000
                
                # Log metrics
                metrics.log_request(
                    endpoint="/api/review",
                    task_type="code_review",
                    model_used=cached_result.get("model_info", {}).get("model_name", "cached"),
                    provider="cache",
                    tokens_used=0,
                    processing_time_ms=processing_time,
                    status="success_cached"
                )
                
                return APIResponse(
                    status=ResponseStatus.SUCCESS,
                    message="Code review completed (cached)",
                    data=cached_result.get("data"),
                    model_info=ModelInfo(**cached_result.get("model_info", {})),
                    request_id=request_id
                )
        
        # 3. PROCESS REQUEST
        result = await analyzer.analyze(
            code=sanitized_code,
            language=req.language.value,
            context=req.context,
            check_style=req.check_style,
            check_security=req.check_security,
            check_performance=req.check_performance
        )
        
        # 4. PARSE AND NORMALIZE RESPONSE
        model_info_data = result.pop("model_info", {})
        normalized_result = ResponseParser.normalize_code_review(
            result.get("raw_response", str(result))
        )
        
        # Merge with existing result
        normalized_result.update({
            k: v for k, v in result.items() 
            if k not in normalized_result and k != "raw_response"
        })
        
        processing_time = (time.time() - start_time) * 1000
        
        model_info = ModelInfo(
            model_name=model_info_data.get("model", "unknown"),
            provider=model_info_data.get("provider", "unknown"),
            tokens_used=model_info_data.get("tokens_used"),
            processing_time_ms=processing_time
        )
        
        # 5. CACHE RESULT
        if settings.CACHE_ENABLED:
            await cache.set(
                cache_key,
                {
                    "data": normalized_result,
                    "model_info": model_info.dict()
                },
                ttl=settings.CACHE_TTL_CODE_REVIEW
            )
            logger.info(f"Cached review result for {request_id}")
        
        # 6. LOG METRICS
        metrics.log_request(
            endpoint="/api/review",
            task_type="code_review",
            model_used=model_info.model_name,
            provider=model_info.provider,
            tokens_used=model_info.tokens_used or 0,
            processing_time_ms=processing_time,
            status="success"
        )
        
        logger.info(f"Code review completed: {request_id} ({processing_time:.2f}ms)")
        
        return APIResponse(
            status=ResponseStatus.SUCCESS,
            message="Code review completed successfully",
            data=normalized_result,
            model_info=model_info,
            request_id=request_id
        )
        
    except ValidationException as e:
        logger.error(f"Validation failed {request_id}: {e.message}")
        metrics.log_request(
            endpoint="/api/review",
            task_type="code_review",
            model_used="none",
            provider="none",
            tokens_used=0,
            processing_time_ms=(time.time() - start_time) * 1000,
            status="validation_error",
            error=e.message
        )
        raise HTTPException(status_code=400, detail=e.message)
        
    except AIAssistantException as e:
        logger.error(f"Code review failed {request_id}: {e.message}")
        metrics.log_request(
            endpoint="/api/review",
            task_type="code_review",
            model_used="unknown",
            provider="unknown",
            tokens_used=0,
            processing_time_ms=(time.time() - start_time) * 1000,
            status="error",
            error=e.message
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)
        
    except Exception as e:
        logger.exception(f"Unexpected error in code review {request_id}")
        metrics.log_request(
            endpoint="/api/review",
            task_type="code_review",
            model_used="unknown",
            provider="unknown",
            tokens_used=0,
            processing_time_ms=(time.time() - start_time) * 1000,
            status="error",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))