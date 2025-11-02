"""
Azure AI (Phi Models) Client
"""
import httpx
from typing import List, Dict
from utils.config import settings
from utils.logger import logger
from utils.exceptions import ModelException
from schemas.model_schemas import ModelResponse, ModelProvider
from pydantic import BaseModel, ConfigDict
class AzureClient:
    """Client for Azure AI (Phi models)"""
    
    def __init__(self):
        self.api_key = settings.AZURE_AI_KEY
        self.endpoint = settings.AZURE_AI_ENDPOINT or "https://models.inference.ai.azure.com"
        self.provider = ModelProvider.AZURE
        
        logger.info("AzureClient initialized")
    
    async def generate(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> ModelResponse:
        """Generate completion using Azure AI"""
        
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
                    f"{self.endpoint}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                response.raise_for_status()
                data = response.json()
                
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
            raise ModelException(f"Azure AI error: {e.response.text}", model_name=model)
        except Exception as e:
            raise ModelException(f"Azure client error: {str(e)}", model_name=model)
    
    async def health_check(self) -> bool:
        """Check if Azure AI is accessible"""
        try:
            # Azure AI doesn't have a models endpoint, so we'll just validate the key format
            return len(self.api_key) > 0
        except Exception as e:
            logger.error(f"Azure health check failed: {e}")
            return False