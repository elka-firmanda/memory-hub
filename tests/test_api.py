from pathlib import Path

from fastapi.testclient import TestClient

from memory_hub.api import app, get_db
from memory_hub.db import MemoryDB


def test_api_create_search_and_context(tmp_path: Path):
    db = MemoryDB(tmp_path / "api.sqlite")
    db.init()

    def override_db():
        return db

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        created = client.post(
            "/memories",
            json={
                "type": "fact",
                "title": "Cloudflare tunnel",
                "content": "Expose memory hub through Cloudflare Tunnel with Access enabled",
                "project": "memory-hub",
                "tags": ["cloudflare", "security"],
                "source_agent": "test",
            },
        )
        assert created.status_code == 200
        memory_id = created.json()["id"]

        loaded = client.get(f"/memories/{memory_id}")
        assert loaded.status_code == 200
        assert loaded.json()["title"] == "Cloudflare tunnel"

        searched = client.get("/search", params={"q": "cloudflare", "project": "memory-hub"})
        assert searched.status_code == 200
        assert searched.json()[0]["memory"]["id"] == memory_id

        context = client.get("/context", params={"project": "memory-hub", "goal": "deploy securely"})
        assert context.status_code == 200
        assert "Cloudflare Tunnel" in context.text
    finally:
        app.dependency_overrides.clear()


def test_health_endpoint_is_public_when_token_is_configured(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MEMORY_HUB_TOKEN", "test-token")
    db = MemoryDB(tmp_path / "health.sqlite")
    db.init()

    def override_db():
        return db

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    finally:
        app.dependency_overrides.clear()


def test_mcp_endpoint_requires_auth_when_token_is_configured(monkeypatch):
    monkeypatch.setenv("MEMORY_HUB_TOKEN", "test-token")
    client = TestClient(app)

    response = client.post("/mcp/", json={})

    assert response.status_code == 401
