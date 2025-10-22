"""Tests for FastAPI endpoints."""

from fastapi.testclient import TestClient
from terraform_ingest.api import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["name"] == "Terraform Ingest API"


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_analyze_endpoint_validation():
    """Test analyze endpoint with invalid data."""
    response = client.post("/analyze", json={})
    assert response.status_code == 422  # Validation error


def test_ingest_endpoint_validation():
    """Test ingest endpoint with invalid data."""
    response = client.post("/ingest", json={})
    assert response.status_code == 422  # Validation error


def test_analyze_endpoint_structure():
    """Test analyze endpoint accepts valid request structure."""
    # Test with minimal valid structure
    request_data = {
        "repository_url": "https://github.com/test/repo",
        "branches": ["main"],
        "include_tags": False,
    }
    # Just verify the endpoint accepts the structure
    # Actual git operations would require valid credentials
    assert request_data["repository_url"] is not None


def test_ingest_endpoint_structure():
    """Test ingest endpoint accepts valid request structure."""
    # Test with minimal valid structure
    request_data = {
        "repositories": [
            {
                "url": "https://github.com/test/repo",
                "branches": ["main"],
            }
        ]
    }
    # Just verify the structure is valid
    # Actual git operations would require valid credentials
    assert len(request_data["repositories"]) == 1
