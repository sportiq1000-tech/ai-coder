"""
Authentication Tests - Verify API key validation
Based on Security Report Section 9.1
"""
import pytest
from httpx import AsyncClient


class TestAuthentication:
    """Test suite for API authentication"""
    
    @pytest.mark.asyncio
    async def test_no_api_key_rejected(self, client: AsyncClient, no_auth_headers):
        """Test that requests without API key are rejected with 401"""
        response = await client.post(
            "/api/review",
            headers=no_auth_headers,
            json={
                "code": "def test(): pass",
                "language": "python"
            }
        )
        
        assert response.status_code == 401
        # Fix: Handle both string and dict responses
        detail = response.json().get("detail", "")
        if isinstance(detail, dict):
            detail = str(detail)
        assert "api key" in detail.lower() or "unauthorized" in detail.lower()
    
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self, client: AsyncClient, invalid_headers):
        """Test that invalid API keys are rejected with 403"""
        response = await client.post(
            "/api/review",
            headers=invalid_headers,
            json={
                "code": "def test(): pass",
                "language": "python"
            }
        )
        
        assert response.status_code == 403
        # Fix: Handle both string and dict responses
        detail = response.json().get("detail", "")
        if isinstance(detail, dict):
            detail = str(detail)
        assert "invalid" in detail.lower() or "forbidden" in detail.lower()
    
    
    @pytest.mark.asyncio
    async def test_valid_api_key_accepted(self, client: AsyncClient, ui_headers, sample_code):
        """Test that valid API keys are accepted"""
        response = await client.post(
            "/api/review",
            headers=ui_headers,
            json={
                "code": sample_code["python"],
                "language": "python"
            }
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    
    
    @pytest.mark.asyncio
    async def test_ui_key_cannot_access_admin(self, client: AsyncClient, ui_headers):
        """Test that UI key cannot access admin endpoints"""
        response = await client.get(
            "/api/admin/metrics",
            headers=ui_headers
        )
        
        assert response.status_code == 403
        # Fix: Handle both string and dict responses
        detail = response.json().get("detail", "")
        if isinstance(detail, dict):
            detail = str(detail)
        assert "admin" in detail.lower() or "forbidden" in detail.lower()
    
    
    @pytest.mark.asyncio
    async def test_admin_key_can_access_admin(self, client: AsyncClient, admin_headers):
        """Test that admin key can access admin endpoints"""
        response = await client.get(
            "/api/admin/metrics",
            headers=admin_headers
        )
        
        assert response.status_code == 200