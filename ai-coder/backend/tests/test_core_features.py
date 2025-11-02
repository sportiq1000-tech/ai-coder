"""
Core Features Tests - Verify all main endpoints work correctly
Tests the 4 core features: Review, Document, Bugs, Generate
"""
import pytest
from httpx import AsyncClient


class TestCoreFeatures:
    """Test suite for core API features"""
    
    @pytest.mark.asyncio
    async def test_code_review_endpoint(self, client: AsyncClient, ui_headers, sample_code):
        """Test code review functionality"""
        response = await client.post(
            "/api/review",
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
        sample_code
    ):
        """Test documentation generation"""
        response = await client.post(
            "/api/document",
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
    async def test_bug_prediction_endpoint(self, client: AsyncClient, ui_headers, sample_code):
        """Test bug prediction functionality"""
        response = await client.post(
            "/api/predict-bugs",
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
    async def test_code_generation_endpoint(self, client: AsyncClient, ui_headers):
        """Test code generation from natural language"""
        response = await client.post(
            "/api/generate",
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
    async def test_health_endpoint(self, client: AsyncClient):
        """Test health check endpoint (no auth required)"""
        response = await client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "models_available" in data