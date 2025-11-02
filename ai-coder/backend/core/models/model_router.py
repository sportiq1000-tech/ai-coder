"""
Model Router - Central orchestration for model selection and fallback
"""
from typing import Optional, List, Dict, Any
from enum import Enum
import time
from utils.logger import logger
from utils.exceptions import ModelException, RateLimitException, ServiceUnavailableException
from schemas.model_schemas import ModelProvider, ModelConfig, ModelResponse
from core.models.groq_client import GroqClient
from core.models.cerebras_client import CerebrasClient
from core.models.bytez_client import BytezClient
from core.models.azure_client import AzureClient
from pydantic import BaseModel, ConfigDict

class TaskType(str, Enum):
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"
    BUG_PREDICTION = "bug_prediction"
    CODE_GENERATION = "code_generation"


class ModelRouter:
    """
    Routes requests to appropriate models with fallback support
    """
    
    def __init__(self):
        """Initialize model clients"""
        self.groq = GroqClient()
        self.cerebras = CerebrasClient()
        self.bytez = BytezClient()
        self.azure = AzureClient()
        
        # Task-to-model mapping with VERIFIED working models
        self.task_mapping = {
            TaskType.CODE_REVIEW: [
                (self.groq, "llama-3.3-70b-versatile"),
                (self.cerebras, "llama-3.3-70b"),
                (self.azure, "Phi-3-mini-4k-instruct")
            ],
            TaskType.DOCUMENTATION: [
                (self.azure, "Phi-3-mini-4k-instruct"),
                (self.groq, "llama-3.1-8b-instant"),
                (self.cerebras, "llama3.1-8b")
            ],
            TaskType.BUG_PREDICTION: [
                (self.groq, "groq/compound"),
                (self.groq, "llama-3.3-70b-versatile"),
                (self.cerebras, "llama-3.3-70b"),
            ],
            TaskType.CODE_GENERATION: [
                (self.cerebras, "llama-3.3-70b"),
                (self.groq, "llama-3.3-70b-versatile"),
                (self.azure, "Phi-3-mini-4k-instruct")
            ]
        }
        
        logger.info("ModelRouter initialized with all clients")
    
    async def route(
        self,
        task_type: TaskType,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> ModelResponse:
        """
        Route request to appropriate model with fallback
        
        Args:
            task_type: Type of task to perform
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            ModelResponse with generated content
            
        Raises:
            ServiceUnavailableException: If all models fail
        """
        fallback_chain = self.task_mapping.get(task_type)
        
        if not fallback_chain:
            raise ModelException(f"No models configured for task: {task_type}")
        
        errors = []
        
        for idx, (client, model_name) in enumerate(fallback_chain):
            try:
                logger.info(f"Attempting {client.__class__.__name__} with model {model_name}")
                
                start_time = time.time()
                
                response = await client.generate(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                processing_time = (time.time() - start_time) * 1000
                
                logger.info(
                    f"Success with {client.__class__.__name__} "
                    f"({processing_time:.2f}ms)"
                )
                
                return response
                
            except RateLimitException as e:
                error_msg = f"{client.__class__.__name__}: Rate limit exceeded"
                logger.warning(error_msg)
                errors.append(error_msg)
                
                # Try next fallback
                if idx < len(fallback_chain) - 1:
                    continue
                    
            except Exception as e:
                error_msg = f"{client.__class__.__name__}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                
                # Try next fallback
                if idx < len(fallback_chain) - 1:
                    continue
        
        # All fallbacks failed
        error_summary = "; ".join(errors)
        logger.error(f"All models failed for {task_type}: {error_summary}")
        raise ServiceUnavailableException(
            f"All models unavailable for {task_type}. Errors: {error_summary}"
        )
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all model providers
        
        Returns:
            Dictionary with provider availability status
        """
        health = {}
        
        providers = [
            ("groq", self.groq),
            ("cerebras", self.cerebras),
            ("bytez", self.bytez),
            ("azure", self.azure)
        ]
        
        for name, client in providers:
            try:
                is_healthy = await client.health_check()
                health[name] = is_healthy
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                health[name] = False
        
        return health


# Singleton instance
_router_instance: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """Get singleton ModelRouter instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = ModelRouter()
    return _router_instance