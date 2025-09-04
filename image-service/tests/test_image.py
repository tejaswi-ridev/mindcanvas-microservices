import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

client = TestClient(app)

@patch('app.main.generate_image_with_flux')
@pytest.mark.asyncio
async def test_generate_image(mock_generate):
    # Mock the image generation function
    mock_generate.return_value = {
        "image_url": "https://example.com/image.jpg",
        "metadata": {"model": "flux-dev"}
    }

    response = client.post(
        "/image/generate",
        json={
            "prompt": "a beautiful sunset",
            "width": 1024,
            "height": 1024
        },
        headers={"X-User-ID": "1"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "image_url" in data
    assert "prompt" in data

def test_generate_image_without_user_id():
    response = client.post(
        "/image/generate",
        json={"prompt": "test prompt"}
    )
    assert response.status_code == 401

def test_image_history():
    response = client.get(
        "/image/history",
        headers={"X-User-ID": "1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
