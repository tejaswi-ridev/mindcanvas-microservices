import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data


@patch("httpx.AsyncClient.post")
@pytest.mark.asyncio
async def test_login_proxy(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "test_token",
        "user": {"id": 1, "email": "test@example.com"}
    }
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "password"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "test_token"
    assert data["user"]["email"] == "test@example.com"


def test_unauthorized_access():
    response = client.get("/auth/me")
    assert response.status_code == 401
