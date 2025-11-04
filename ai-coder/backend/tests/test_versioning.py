"""
Test API versioning and backward compatibility
"""
import pytest

@pytest.mark.asyncio
async def test_v1_endpoint_returns_version_header(client, api_v1_base):
    """V1 endpoints should include version header"""
    response = await client.get(f"{api_v1_base}/health")
    assert response.status_code == 200
    assert "X-API-Version" in response.headers
    assert response.headers["X-API-Version"] == "1.0"


@pytest.mark.asyncio
async def test_legacy_endpoint_works(client, api_legacy_base, ui_headers):
    """Legacy /api/ endpoints should still work"""
    response = await client.post(
        f"{api_legacy_base}/review",
        json={"code": "print('test')", "language": "python"},
        headers=ui_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_legacy_endpoint_marked_deprecated(client, api_legacy_base, ui_headers):
    """Legacy endpoints should be marked as deprecated"""
    response = await client.post(
        f"{api_legacy_base}/review",
        json={"code": "print('test')", "language": "python"},
        headers=ui_headers
    )
    assert response.headers.get("X-API-Deprecated") == "true"
    assert "X-API-Migration" in response.headers


@pytest.mark.asyncio
async def test_v1_not_marked_deprecated(client, api_v1_base, ui_headers):
    """V1 endpoints should NOT be marked deprecated"""
    response = await client.post(
        f"{api_v1_base}/review",
        json={"code": "print('test')", "language": "python"},
        headers=ui_headers
    )
    assert "X-API-Deprecated" not in response.headers or response.headers.get("X-API-Deprecated") != "true"


@pytest.mark.asyncio
async def test_admin_endpoints_versioned(client, api_v1_base, admin_headers):
    """Admin endpoints should be under v1"""
    response = await client.get(
        f"{api_v1_base}/admin/metrics",
        headers=admin_headers
    )
    # Should work (200) or require auth (401/403), but not 404
    assert response.status_code != 404


@pytest.mark.asyncio
async def test_openapi_docs_show_v1(client):
    """OpenAPI docs should show v1 endpoints"""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    paths = list(spec["paths"].keys())
    
    # Should have v1 endpoints
    v1_paths = [p for p in paths if p.startswith("/api/v1/")]
    assert len(v1_paths) > 0, "No v1 endpoints found in OpenAPI spec"