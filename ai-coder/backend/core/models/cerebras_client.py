"""
Cerebras API Client
"""
import httpx
from typing import List, Dict
from utils.config import settings
from utils.logger import logger
from utils.exceptions import ModelException, RateLimitException
from schemas.model_schemas import ModelResponse, ModelProvider
from pydantic import BaseModel, ConfigDict
class CerebrasClient:
    """Client for Cerebras API"""
    
    def __init__(self):
        self.api_key = settings.CEREBRAS_API_KEY
        self.base_url = settings.CEREBRAS_BASE_URL
        self.provider = ModelProvider.CEREBRAS
        self.token_count = 0
        
        logger.info("CerebrasClient initialized")
    
    async def generate(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> ModelResponse:
        """Generate completion using Cerebras"""
        
        # Check token limit
        if self.token_count >= settings.CEREBRAS_TOKEN_LIMIT * settings.RATE_LIMIT_THRESHOLD:
            raise RateLimitException(f"Cerebras token limit approaching: {self.token_count}")
        
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
                
                content = data["choices"][0]["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens", 0)
                
                # Update token counter
                self.token_count += tokens_used
                
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
                raise RateLimitException("Cerebras rate limit exceeded")
            raise ModelException(f"Cerebras API error: {e.response.text}", model_name=model)
        except Exception as e:
            raise ModelException(f"Cerebras client error: {str(e)}", model_name=model)
    
    async def health_check(self) -> bool:
        """Check if Cerebras API is accessible"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try a minimal request
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Cerebras health check failed: {e}")
            return False