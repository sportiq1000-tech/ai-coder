"""
Groq API Client
"""
import httpx
from typing import List, Dict, Optional
from utils.config import settings
from utils.logger import logger
from utils.exceptions import ModelException, RateLimitException
from schemas.model_schemas import ModelResponse, ModelProvider
from pydantic import BaseModel, ConfigDict
class GroqClient:
    """Client for Groq API"""
    
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.base_url = settings.GROQ_BASE_URL
        self.provider = ModelProvider.GROQ
        
        # Rate limiting tracking
        self.request_count = 0
        self.daily_request_count = 0
        
        logger.info("GroqClient initialized")
    
    async def generate(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> ModelResponse:
        """
        Generate completion using Groq
        
        Args:
            model: Model name
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            
        Returns:
            ModelResponse object
        """
        # Check rate limits
        if self.request_count >= settings.GROQ_RPM_LIMIT * settings.RATE_LIMIT_THRESHOLD:
            raise RateLimitException(f"Groq RPM limit approaching: {self.request_count}")
        
        if self.daily_request_count >= settings.GROQ_RPD_LIMIT * settings.RATE_LIMIT_THRESHOLD:
            raise RateLimitException(f"Groq daily limit approaching: {self.daily_request_count}")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Update rate limit counters
                self.request_count += 1
                self.daily_request_count += 1
                
                # Extract response
                content = data["choices"][0]["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens")
                
                return ModelResponse(
                    content=content,
                    model=model,
                    provider=self.provider.value,
                    tokens_used=tokens_used,
                    finish_reason=data["choices"][0].get("finish_reason"),
                    metadata={"usage": data.get("usage")}
                )
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitException("Groq rate limit exceeded")
            raise ModelException(f"Groq API error: {e.response.text}", model_name=model)
        except Exception as e:
            raise ModelException(f"Groq client error: {str(e)}", model_name=model)
    
    async def health_check(self) -> bool:
        """Check if Groq API is accessible"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Groq health check failed: {e}")
            return False