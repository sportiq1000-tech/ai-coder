import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_document_endpoint_success(ui_headers):
    """Test successful documentation generation"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('api.routes.document.doc_generator.generate') as mock_gen:
            mock_gen.return_value = {
                "documentation": "Generated docs",
                "model_info": {
                    "model": "gpt-4",
                    "provider": "openai",
                    "tokens_used": 100
                }
            }
            
            response = await client.post(
                "/api/v1/document",
                json={
                    "code": "def test(): pass",
                    "language": "python",
                    "format": "markdown"
                },
                headers=ui_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # FIX: Response has 'data' wrapper
            assert "data" in data
            assert "documentation" in data["data"]  # ← Fixed
            assert data["data"]["documentation"] == "Generated docs"
            
            # Also verify other fields
            assert "model_info" in data
            assert data["model_info"]["model_name"] == "gpt-4"


@pytest.mark.asyncio
async def test_document_validation_error(ui_headers):
    """Test validation error handling"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/document",
            json={
                "code": "",  # Empty code should fail validation
                "language": "python"
            },
            headers=ui_headers
        )
        
        # FIX: FastAPI returns 422 for validation errors
        assert response.status_code == 422  # ← Changed from 400
        
        # Optionally verify error details
        data = response.json()
        assert "detail" in data


@pytest.mark.asyncio
async def test_document_cache_hit(ui_headers):
    """Test cache hit scenario"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('api.routes.document.get_cache') as mock_cache_getter:
            mock_cache = AsyncMock()
            
            # FIX: Use correct ModelInfo schema
            mock_cache.get.return_value = {
                "data": {"documentation": "cached result"},
                "model_info": {
                    "model_name": "cached-model",  # ← Changed from 'model'
                    "provider": "cached-provider",  # ← Added required field
                    "tokens_used": 100,
                    "processing_time_ms": 50.0
                }
            }
            mock_cache_getter.return_value = mock_cache
            
            response = await client.post(
                "/api/v1/document",
                json={
                    "code": "def cached(): pass",
                    "language": "python",
                    "format": "markdown"
                },
                headers=ui_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify cache was used
            assert "data" in data
            assert data["data"]["documentation"] == "cached result"
            
            # Verify cache.get was called
            mock_cache.get.assert_called_once()