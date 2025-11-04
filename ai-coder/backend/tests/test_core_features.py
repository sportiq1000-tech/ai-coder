"""
Core Features Tests - Verify all main endpoints work correctly
Tests the 4 core features: Review, Document, Bugs, Generate
"""
import pytest
from httpx import AsyncClient


class TestCoreFeatures:
    """Test suite for core API features"""
    
    @pytest.mark.asyncio
    async def test_code_review_endpoint(self, client: AsyncClient, ui_headers, sample_code, api_v1_base):
        """Test code review functionality"""
        response = await client.post(
            f"{api_v1_base}/review",
            headers=ui_headers,
            json={
                "code": sample_code["python"],
                "language": "python",
                "check_style": True,
                "check_security": True,
                "check_performance": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "summary" in data or "data" in data
    
    
    @pytest.mark.asyncio
    async def test_documentation_generation_endpoint(
        self,
        client: AsyncClient,
        ui_headers,
        sample_code,
        api_v1_base
    ):
        """Test documentation generation"""
        response = await client.post(
            f"{api_v1_base}/document",
            headers=ui_headers,
            json={
                "code": sample_code["python"],
                "language": "python",
                "format": "markdown",
                "include_examples": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    
    @pytest.mark.asyncio
    async def test_bug_prediction_endpoint(self, client: AsyncClient, ui_headers, sample_code, api_v1_base):
        """Test bug prediction functionality"""
        response = await client.post(
            f"{api_v1_base}/predict-bugs",
            headers=ui_headers,
            json={
                "code": sample_code["python"],
                "language": "python",
                "severity_threshold": "medium"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    
    @pytest.mark.asyncio
    async def test_code_generation_endpoint(self, client: AsyncClient, ui_headers, api_v1_base):
        """Test code generation from natural language"""
        response = await client.post(
            f"{api_v1_base}/generate",
            headers=ui_headers,
            json={
                "description": "Create a function that adds two numbers",
                "language": "python",
                "include_tests": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient, api_v1_base):
        """Test health check endpoint (no auth required)"""
        response = await client.get(f"{api_v1_base}/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "models_available" in data
    
    
    @pytest.mark.asyncio
    async def test_legacy_api_backward_compatibility(self, client: AsyncClient, ui_headers, sample_code, api_legacy_base):
        """Test that legacy /api/ routes still work for backward compatibility"""
        response = await client.post(
            f"{api_legacy_base}/review",
            headers=ui_headers,
            json={
                "code": sample_code["python"],
                "language": "python",
                "check_style": True,
                "check_security": True,
                "check_performance": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        # Should include deprecation headers
        assert response.headers.get("X-API-Version") == "1.0"
        assert response.headers.get("X-API-Deprecated") == "true"