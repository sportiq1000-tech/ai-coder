"""
Code Generation API endpoint with validation and parsing
"""
from fastapi import APIRouter, HTTPException, Request  # Add Request
from schemas.request_schemas import CodeGenerationRequest
from schemas.response_schemas import APIResponse, ResponseStatus, ModelInfo
from core.processors.code_generator import CodeGenerator
from utils.logger import logger
from utils.exceptions import AIAssistantException, ValidationException
from utils.validators import RequestValidator, sanitizer
from utils.parsers import ResponseParser
from utils.cache import get_cache, Cache
from utils.metrics import get_metrics
from utils.config import settings
import time
import uuid
from utils.security_monitor import security_monitor

router = APIRouter()
code_generator = CodeGenerator()


@router.post("/generate", response_model=APIResponse)
async def generate_code(req: CodeGenerationRequest, request: Request):  # Add request param
    """
    Generate code from natural language description
    
    - **description**: Description of what the code should do (required)
    - **language**: Target programming language
    - **context**: Additional context (optional)
    - **include_tests**: Include unit tests (default: false)
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    cache = get_cache()
    metrics = get_metrics()
    
    logger.info(f"Code generation request {request_id}: {req.language}")
    
    try:
               # VALIDATION
        RequestValidator.validate_description(req.description)  # FIXED: req
        RequestValidator.validate_context(req.context)  # FIXED: req
        
        # SECURITY FIX - Phase 2C: Check description for prompt injection
        is_injection_desc, pattern_desc = sanitizer.check_prompt_injection(req.description)
        if is_injection_desc:
            # Log the security block
            security_monitor.log_blocked_request(
                request_id=request_id,
                endpoint="/api/generate",
                client_ip=request.client.host,
                api_key_user="authenticated",
                input_data=req.description,
                block_reason="Suspicious input detected in description",
                matched_pattern=pattern_desc,
                attack_type="prompt_injection"
            )
            logger.warning(f"Prompt injection detected in description for {request_id}")
            raise ValidationException("Suspicious input detected in description")
        
        # Check context if provided
        if req.context:
            is_injection_ctx, pattern_ctx = sanitizer.check_prompt_injection(req.context)
            if is_injection_ctx:
                # Log the security block
                security_monitor.log_blocked_request(
                    request_id=request_id,
                    endpoint="/api/generate",
                    client_ip=request.client.host,
                    api_key_user="authenticated",
                    input_data=req.context,
                    block_reason="Suspicious input detected in context",
                    matched_pattern=pattern_ctx,
                    attack_type="prompt_injection"
                )
                logger.warning(f"Prompt injection detected in context for {request_id}")
                raise ValidationException("Suspicious input detected in context")
        
        # CHECK CACHE (rest of your code continues...)
        # CHECK CACHE
        if settings.CACHE_ENABLED:
            cache_key = f"generate:{Cache.generate_key(req.description, req.language, req.include_tests, req.context)}"
            cached_result = await cache.get(cache_key)
            
            if cached_result:
                logger.info(f"Cache hit for code generation {request_id}")
                processing_time = (time.time() - start_time) * 1000
                
                metrics.log_request(
                    endpoint="/api/generate",
                    task_type="code_generation",
                    model_used="cached",
                    provider="cache",
                    tokens_used=0,
                    processing_time_ms=processing_time,
                    status="success_cached"
                )
                
                return APIResponse(
                    status=ResponseStatus.SUCCESS,
                    message="Code generated (cached)",
                    data=cached_result.get("data"),
                    model_info=ModelInfo(**cached_result.get("model_info", {})),
                    request_id=request_id
                )
        
        # PROCESS REQUEST
        result = await code_generator.generate(
            description=req.description,
            language=req.language.value,
            context=req.context,
            include_tests=req.include_tests
        )
        
        # PARSE AND NORMALIZE
        model_info_data = result.pop("model_info", {})
        normalized_result = ResponseParser.normalize_code_generation(
            result.get("raw_response", str(result)),
            req.language.value
        )
        
        # Merge results
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
        
        # CACHE RESULT (shorter TTL for generation)
        if settings.CACHE_ENABLED:
            await cache.set(
                cache_key,
                {
                    "data": normalized_result,
                    "model_info": model_info.dict()
                },
                ttl=settings.CACHE_TTL_CODE_GENERATION
            )
        
        # LOG METRICS
        metrics.log_request(
            endpoint="/api/generate",
            task_type="code_generation",
            model_used=model_info.model_name,
            provider=model_info.provider,
            tokens_used=model_info.tokens_used or 0,
            processing_time_ms=processing_time,
            status="success"
        )
        
        logger.info(f"Code generation completed: {request_id} ({processing_time:.2f}ms)")
        
        return APIResponse(
            status=ResponseStatus.SUCCESS,
            message="Code generated successfully",
            data=normalized_result,
            model_info=model_info,
            request_id=request_id
        )
        
    except ValidationException as e:
        logger.error(f"Validation failed {request_id}: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
        
    except AIAssistantException as e:
        logger.error(f"Code generation failed {request_id}: {e.message}")
        metrics.log_request(
            endpoint="/api/generate",
            task_type="code_generation",
            model_used="unknown",
            provider="unknown",
            tokens_used=0,
            processing_time_ms=(time.time() - start_time) * 1000,
            status="error",
            error=e.message
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)
        
    except Exception as e:
        logger.exception(f"Unexpected error in code generation {request_id}")
        raise HTTPException(status_code=500, detail=str(e))