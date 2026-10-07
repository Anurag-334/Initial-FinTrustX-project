"""
=========================================================
Integration Tests: Health & Metadata Endpoints
=========================================================
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture(scope="module")
def client():
    """Create test client with lifespan execution."""
    with TestClient(app) as test_client:
        yield test_client


def test_root_endpoint(client):
    """Test GET / returns API metadata and documentation link."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "documentation" in data
    assert data["documentation"] == "/docs"


def test_health_endpoint(client):
    """Test GET /health returns healthy status and loaded model info."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["pipeline_loaded"] is True
    assert data["model"] == "xgboost"


def test_model_info_endpoint(client):
    """Test GET /model-info returns model architecture and static benchmark metrics."""
    response = client.get("/model-info")
    assert response.status_code == 200
    data = response.json()
    assert "model_name" in data
    assert data["task"] == "Binary Credit Risk Classification"
    assert data["n_raw_features"] == 121
    assert data["n_preprocessed_features"] == 245
