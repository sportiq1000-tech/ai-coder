"""
Bug Prediction API endpoint with validation and caching
"""
from fastapi import APIRouter, HTTPException, Request
from schemas.request_schemas import BugPredictionRequest
from schemas.response_schemas import APIResponse, ResponseStatus, ModelInfo
from core.processors.bug_predictor import BugPredictor
from utils.logger import logger
from utils.exceptions import AIAssistantException, ValidationException
from utils.validators import CodeValidator, sanitizer
from utils.parsers import ResponseParser
from utils.cache import get_cache, Cache
from utils.metrics import get_metrics
from utils.config import settings
import time
import uuid

router = APIRouter()
bug_predictor = BugPredictor()


@router.post("/predict-bugs", response_model=APIResponse)
async def predict_bugs(req: BugPredictionRequest, request: Request):
    """
    Predict potential bugs in code with validation
    
    - **code**: Code to analyze (required)
    - **language**: Programming language
    - **context**: Additional context (optional)
    - **severity_threshold**: Minimum severity to report - low, medium, high (default: medium)
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    cache = get_cache()
    metrics = get_metrics()
    
    logger.info(f"Bug prediction request {request_id}: {req.language}")
    
    try:
        # VALIDATION
        CodeValidator.validate_code_length(
            req.code,
            min_length=settings.MIN_CODE_LENGTH,
            max_length=settings.MAX_CODE_LENGTH
        )
        
        sanitized_code = CodeValidator.sanitize_code(req.code)
         # SECURITY FIX - Phase 2: Validate input for prompt injection
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
        # Security pre-check
        if settings.VALIDATE_CODE_SECURITY:
            is_safe, security_issues = CodeValidator.check_security_issues(sanitized_code)
            if not is_safe:
                logger.info(f"Pre-detected {len(security_issues)} security patterns")
        
        # CHECK CACHE
        if settings.CACHE_ENABLED:
            cache_key = f"bugs:{Cache.generate_key(sanitized_code, req.language, req.severity_threshold)}"
            cached_result = await cache.get(cache_key)
            
            if cached_result:
                logger.info(f"Cache hit for bug prediction {request_id}")
                processing_time = (time.time() - start_time) * 1000
                
                metrics.log_request(
                    endpoint="/api/predict-bugs",
                    task_type="bug_prediction",
                    model_used="cached",
                    provider="cache",
                    tokens_used=0,
                    processing_time_ms=processing_time,
                    status="success_cached"
                )
                
                return APIResponse(
                    status=ResponseStatus.SUCCESS,
                    message="Bug prediction completed (cached)",
                    data=cached_result.get("data"),
                    model_info=ModelInfo(**cached_result.get("model_info", {})),
                    request_id=request_id
                )
        
        # PROCESS REQUEST
        result = await bug_predictor.predict(
            code=sanitized_code,
            language=req.language.value,
            context=req.context,
            severity_threshold=req.severity_threshold
        )
        
        # PARSE AND NORMALIZE
        model_info_data = result.pop("model_info", {})
        normalized_result = ResponseParser.normalize_bug_prediction(
            result.get("raw_response", str(result))
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
        
        # CACHE RESULT
        if settings.CACHE_ENABLED:
            await cache.set(
                cache_key,
                {
                    "data": normalized_result,
                    "model_info": model_info.dict()
                },
                ttl=settings.CACHE_TTL_BUG_PREDICTION
            )
        
        # LOG METRICS
        metrics.log_request(
            endpoint="/api/predict-bugs",
            task_type="bug_prediction",
            model_used=model_info.model_name,
            provider=model_info.provider,
            tokens_used=model_info.tokens_used or 0,
            processing_time_ms=processing_time,
            status="success"
        )
        
        logger.info(f"Bug prediction completed: {request_id} ({processing_time:.2f}ms)")
        
        return APIResponse(
            status=ResponseStatus.SUCCESS,
            message="Bug prediction completed successfully",
            data=normalized_result,
            model_info=model_info,
            request_id=request_id
        )
        
    except ValidationException as e:
        logger.error(f"Validation failed {request_id}: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
        
    except AIAssistantException as e:
        logger.error(f"Bug prediction failed {request_id}: {e.message}")
        metrics.log_request(
            endpoint="/api/predict-bugs",
            task_type="bug_prediction",
            model_used="unknown",
            provider="unknown",
            tokens_used=0,
            processing_time_ms=(time.time() - start_time) * 1000,
            status="error",
            error=e.message
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)
        
    except Exception as e:
        logger.exception(f"Unexpected error in bug prediction {request_id}")
        raise HTTPException(status_code=500, detail=str(e))