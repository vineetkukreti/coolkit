"""Shared pytest fixtures for auth + isolation tests.

Points the db module's file paths at a per-test temp dir, resets the route
modules' thread-local connection caches (so a connection opened against a prior
test's temp DB can't leak forward), and exposes a configured TestClient.
"""

import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

import db  # noqa: E402

# Route modules that keep a thread-local connection cache.
_CACHED_ROUTE_MODULES = [
    "routes.pipeline", "routes.email", "routes.posts", "routes.leads",
    "routes.settings", "routes.scraper", "routes.tools", "routes.skills_intel",
]


@pytest.fixture
def tmp_data(tmp_path, monkeypatch):
    """Redirect all DB files into an isolated temp dir for this test."""
    monkeypatch.setattr(db, "AUTH_DB_PATH", tmp_path / "auth.db")
    monkeypatch.setattr(db, "USERS_DIR", tmp_path / "users")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "legacy.db")

    # Reset per-module thread-local caches so no thread holds a connection to a
    # previous test's (now-deleted) temp database.
    import importlib
    for name in _CACHED_ROUTE_MODULES:
        mod = importlib.import_module(name)
        mod._local = threading.local()

    yield tmp_path


@pytest.fixture
def client(tmp_data):
    from fastapi.testclient import TestClient
    import server
    return TestClient(server.app)


@pytest.fixture
def make_user(client):
    """Return a helper that registers a user and returns (auth_headers, user)."""
    def _make(email, password="secret123", name=""):
        res = client.post("/api/auth/register", json={"email": email, "password": password, "name": name})
        assert res.status_code == 200, res.text
        body = res.json()
        return {"Authorization": f"Bearer {body['token']}"}, body["user"]
    return _make
