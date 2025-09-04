import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

client = TestClient(app)

@patch('app.main.search_with_tavily')
@pytest.mark.asyncio
async def test_search_endpoint(mock_search):
    # Mock the search function
    mock_search.return_value = [
        {
            "title": "Test Result",
            "url": "https://example.com",
            "snippet": "This is a test search result"
        }
    ]

    response = client.post(
        "/search/",
        json={"query": "test query"},
        headers={"X-User-ID": "1"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) > 0

def test_search_without_user_id():
    response = client.post(
        "/search/",
        json={"query": "test query"}
    )
    assert response.status_code == 401

def test_search_history():
    response = client.get(
        "/search/history",
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
