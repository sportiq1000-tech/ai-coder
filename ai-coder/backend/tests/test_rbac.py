"""
RBAC (Role-Based Access Control) Tests
Verify that different user tiers have appropriate access levels
"""
import pytest
from httpx import AsyncClient


class TestRBAC:
    """Test suite for role-based access control"""
    
    @pytest.mark.asyncio
    async def test_ui_user_basic_access(self, client: AsyncClient, ui_headers, sample_code):
        """Test that UI users can access basic endpoints"""
        endpoints = [
            ("/api/review", {"code": sample_code["python"], "language": "python"}),
            ("/api/document", {"code": sample_code["python"], "language": "python"}),
            ("/api/predict-bugs", {"code": sample_code["python"], "language": "python"}),
            ("/api/generate", {"description": "create hello world", "language": "python"}),
        ]
        
        for endpoint, data in endpoints:
            response = await client.post(endpoint, headers=ui_headers, json=data)
            assert response.status_code == 200, f"UI user should access {endpoint}"
    
    
    @pytest.mark.asyncio
    async def test_ui_user_cannot_access_admin(self, client: AsyncClient, ui_headers):
        """Test that UI users cannot access admin endpoints"""
        admin_endpoints = [
            "/api/admin/metrics",
            "/api/admin/cache/stats",
            "/api/admin/security/stats",
        ]
        
        for endpoint in admin_endpoints:
            response = await client.get(endpoint, headers=ui_headers)
            assert response.status_code == 403, f"UI user should NOT access {endpoint}"
    
    
    @pytest.mark.asyncio
    async def test_developer_cannot_access_admin(self, client: AsyncClient, dev_headers):
        """Test that developer users cannot access admin endpoints"""
        admin_endpoints = [
            "/api/admin/metrics",
            "/api/admin/cache/stats",
        ]
        
        for endpoint in admin_endpoints:
            response = await client.get(endpoint, headers=dev_headers)
            assert response.status_code == 403, f"Developer should NOT access {endpoint}"
    
    
    @pytest.mark.asyncio
    async def test_admin_full_access(self, client: AsyncClient, admin_headers):
        """Test that admin users can access all endpoints"""
        # Admin endpoints
        admin_endpoints = [
            "/api/admin/metrics",
            "/api/admin/cache/stats",
        ]
        
        for endpoint in admin_endpoints:
            response = await client.get(endpoint, headers=admin_headers)
            assert response.status_code == 200, f"Admin should access {endpoint}"