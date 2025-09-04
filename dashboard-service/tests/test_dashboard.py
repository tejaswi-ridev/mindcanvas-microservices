import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from types import SimpleNamespace

# Import the FastAPI app and module-level clients to patch
# Adjust the import path if your project layout differs
from app.main import app
import app.main as dashboard_module


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, key: str):
        v = self.store.get(key)
        if v is None:
            return None
        # Emulate real Redis .get() returning bytes when using setex with bytes/string
        return v if isinstance(v, (bytes, bytearray)) else v

    def setex(self, key: str, ttl: int, value):
        self.store[key] = value

    def delete(self, key: str):
        if key in self.store:
            del self.store[key]


@pytest.fixture(autouse=True)
def patch_redis_and_clients(monkeypatch):
    # Patch redis_client with an in-memory fake
    fake_redis = FakeRedis()
    monkeypatch.setattr(dashboard_module, "redis_client", fake_redis, raising=True)

    # Patch gRPC client methods with AsyncMock
    # search_client
    monkeypatch.setattr(
        dashboard_module.search_client,
        "get_search_history",
        AsyncMock(return_value=[
            {"id": 101, "query": "tree", "result_count": 5, "created_at": "2025-09-04T10:00:00Z"},
            {"id": 102, "query": "banana", "result_count": 8, "created_at": "2025-09-04T10:01:00Z"},
        ]),
        raising=True,
    )
    monkeypatch.setattr(
        dashboard_module.search_client,
        "get_search_count",
        AsyncMock(return_value=12),
        raising=True,
    )

    # image_client
    monkeypatch.setattr(
        dashboard_module.image_client,
        "get_image_history",
        AsyncMock(return_value=[
            {"id": 201, "prompt": "a beautiful sunset", "image_url": "http://example.com/sunset.jpg", "created_at": "2025-09-04T10:02:00Z"},
            {"id": 202, "prompt": "a car", "image_url": "http://example.com/car.jpg", "created_at": "2025-09-04T10:03:00Z"},
        ]),
        raising=True,
    )
    monkeypatch.setattr(
        dashboard_module.image_client,
        "get_image_count",
        AsyncMock(return_value=7),
        raising=True,
    )

    # Also patch delete ops for completeness (used by delete endpoints)
    monkeypatch.setattr(
        dashboard_module.search_client,
        "delete_search",
        AsyncMock(return_value=True),
        raising=True,
    )
    monkeypatch.setattr(
        dashboard_module.image_client,
        "delete_image",
        AsyncMock(return_value=True),
        raising=True,
    )

    return SimpleNamespace(redis=fake_redis)


client = TestClient(app)


def test_dashboard_search_ok():
    resp = client.get("/dashboard/search?limit=2", headers={"x-user-id": "1"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) == 2
    # CORRECTED: Access the first element of the list (data[0]) before the key
    assert data[0]["query"] == "tree"

def test_dashboard_images_ok():
    resp = client.get("/dashboard/images?limit=2", headers={"x-user-id": "1"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) == 2
    # CORRECTED: Access the first element of the list (data[0]) before the key
    assert data[0]["prompt"] == "a beautiful sunset"

def test_dashboard_stats_ok():
    resp = client.get("/dashboard/stats", headers={"x-user-id": "1"})
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_searches"] == 12
    assert stats["total_images"] == 7


def test_requires_user_header():
    for path in ["/dashboard/search", "/dashboard/images", "/dashboard/stats"]:
        r = client.get(path)
        assert r.status_code == 401


def test_delete_search_ok():
    resp = client.delete("/dashboard/search/101", headers={"x-user-id": "1"})
    assert resp.status_code == 200
    assert resp.json()["message"].lower().startswith("search deleted")


def test_delete_image_ok():
    resp = client.delete("/dashboard/image/201", headers={"x-user-id": "1"})
    assert resp.status_code == 200
    assert resp.json()["message"].lower().startswith("image deleted")


def test_export_csv_ok():
    resp = client.get("/dashboard/export/csv", headers={"x-user-id": "1"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")


def test_export_pdf_ok():
    resp = client.get("/dashboard/export/pdf", headers={"x-user-id": "1"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
