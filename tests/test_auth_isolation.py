"""Auth flow + per-user data isolation tests.

Run: pytest tests/test_auth_isolation.py -v
"""

import db


# ─── Auth flows ──────────────────────────────────────────────────────────────

def test_register_and_login(client):
    r = client.post("/api/auth/register", json={"email": "a@example.com", "password": "secret123"})
    assert r.status_code == 200
    assert r.json()["token"]
    assert r.json()["user"]["email"] == "a@example.com"

    r2 = client.post("/api/auth/login", json={"email": "a@example.com", "password": "secret123"})
    assert r2.status_code == 200
    assert r2.json()["token"]


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json={"email": "b@example.com", "password": "secret123"})
    r = client.post("/api/auth/login", json={"email": "b@example.com", "password": "WRONG"})
    assert r.status_code == 401


def test_duplicate_email_rejected(client):
    client.post("/api/auth/register", json={"email": "c@example.com", "password": "secret123"})
    r = client.post("/api/auth/register", json={"email": "c@example.com", "password": "secret123"})
    assert r.status_code == 409


def test_short_password_rejected(client):
    r = client.post("/api/auth/register", json={"email": "d@example.com", "password": "x"})
    assert r.status_code == 400


def test_unauthenticated_request_401(client):
    # A protected data endpoint must reject calls with no token.
    r = client.get("/api/db/stats")
    assert r.status_code == 401


def test_bad_token_401(client):
    r = client.get("/api/db/stats", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_me_returns_current_user(make_user, client):
    headers, user = make_user("me@example.com")
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "me@example.com"


# ─── Data isolation ──────────────────────────────────────────────────────────

def _seed_post_for(user_id, content="We are hiring an AI Engineer", url="https://example.test/p1"):
    """Insert one post into the given user's private DB."""
    token = db.current_user_id.set(user_id)
    try:
        conn = db.init_db()
        try:
            db.insert_post(conn, {"content": content, "post_url": url, "is_hiring": True})
        finally:
            conn.close()
    finally:
        db.current_user_id.reset(token)


def test_data_is_isolated_per_user(make_user, client):
    headers_a, user_a = make_user("owner-a@example.com")
    headers_b, user_b = make_user("owner-b@example.com")

    # User A has one post; user B has none.
    _seed_post_for(user_a["id"])

    stats_a = client.get("/api/db/stats", headers=headers_a)
    stats_b = client.get("/api/db/stats", headers=headers_b)
    assert stats_a.status_code == 200 and stats_b.status_code == 200

    assert stats_a.json()["total_posts"] == 1, "User A should see their own post"
    assert stats_b.json()["total_posts"] == 0, "User B must NOT see User A's data"


def test_no_bleed_under_interleaved_requests(make_user, client):
    """Guards the per-user (not per-thread) connection cache: repeated, interleaved
    requests from two users on the shared threadpool must never cross over."""
    headers_a, user_a = make_user("loop-a@example.com")
    headers_b, user_b = make_user("loop-b@example.com")

    _seed_post_for(user_a["id"], url="https://example.test/loop-a")

    for _ in range(8):
        a = client.get("/api/db/stats", headers=headers_a).json()["total_posts"]
        b = client.get("/api/db/stats", headers=headers_b).json()["total_posts"]
        assert a == 1
        assert b == 0
