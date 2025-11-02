"""
Error Handling Tests - Verify proper error responses
Tests validation errors, malformed requests, and error formats
"""
import pytest
from httpx import AsyncClient


class TestErrorHandling:
    """Test suite for error handling and validation"""
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, client: AsyncClient, ui_headers):
        """Test that missing required fields return 422"""
        response = await client.post(
            "/api/review",
            headers=ui_headers,
            json={
                # Missing 'code' and 'language'
            }
        )
        
        assert response.status_code == 422
        assert "detail" in response.json()
    
    
    @pytest.mark.asyncio
    async def test_invalid_language(self, client: AsyncClient, ui_headers, sample_code):
        """Test that invalid language is handled"""
        response = await client.post(
            "/api/review",
            headers=ui_headers,
            json={
                "code": sample_code["python"],
                "language": "invalid_language_xyz"
            }
        )
        
        # Should either validate or accept it
        assert response.status_code in [200, 400, 422]
    
    
    @pytest.mark.asyncio
    async def test_code_too_long(self, client: AsyncClient, ui_headers):
        """Test that excessively long code is rejected"""
        very_long_code = "x = 1\n" * 100000  # Way over limit
        
        response = await client.post(
            "/api/review",
            headers=ui_headers,
            json={
                "code": very_long_code,
                "language": "python"
            }
        )
        
        # Should reject with 400 or 422
        assert response.status_code in [400, 422]
    
    
    @pytest.mark.asyncio
    async def test_malformed_json(self, client: AsyncClient, ui_headers):
        """Test that malformed JSON is rejected"""
        response = await client.post(
            "/api/review",
            headers=ui_headers,
            content=b"{ invalid json }"
        )
        
        assert response.status_code == 422
    
    
    @pytest.mark.asyncio
    async def test_empty_code_field(self, client: AsyncClient, ui_headers):
        """Test that empty code is rejected"""
        response = await client.post(
            "/api/review",
            headers=ui_headers,
            json={
                "code": "",  # Empty code
                "language": "python"
            }
        )
        
        # Should reject with 400 or 422
        assert response.status_code in [400, 422]