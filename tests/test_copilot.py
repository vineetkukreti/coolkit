"""Career copilot: extension save-job, autofill profile, weekly goals.

Run: pytest tests/test_copilot.py -v
"""


def _auth(client, email="copilot@example.com"):
    r = client.post("/api/auth/register", json={"email": email, "password": "secret123"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_save_job_from_extension_and_dedup(client):
    h = _auth(client)
    body = {"url": "https://boards.greenhouse.io/acme/jobs/1", "title": "AI Engineer", "company": "Acme",
            "page_text": "We need Python, FastAPI, LLM and healthcare experience. 3+ years.", "status": "applied"}
    r = client.post("/api/extension/save-job", json=body, headers=h).json()
    assert r["status"] == "ok" and r["application_id"]
    assert 0 <= r["ats"]["ats_score"] <= 100

    again = client.post("/api/extension/save-job", json=body, headers=h).json()
    assert again["status"] == "duplicate"


def test_save_job_requires_url(client):
    r = client.post("/api/extension/save-job", json={}, headers=_auth(client, "u2@example.com"))
    assert r.status_code == 400


def test_goals_count_applied_jobs_and_streak(client):
    h = _auth(client, "goals@example.com")
    client.post("/api/goals", json={"applications": 3}, headers=h)
    client.post("/api/extension/save-job", json={"url": "https://x.test/j/1", "status": "applied"}, headers=h)
    g = client.get("/api/goals", headers=h).json()
    apps = next(x for x in g["goals"] if x["metric"] == "applications")
    assert apps["target"] == 3 and apps["done"] == 1 and apps["pct"] == 33
    assert g["streak_days"] == 1 and g["active_today"]


def test_extension_requires_auth(client):
    assert client.get("/api/extension/autofill-profile").status_code == 401


def test_extension_origin_allowed_by_cors(client):
    r = client.options("/api/goals", headers={"Origin": "chrome-extension://abcdef",
                                              "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") == "chrome-extension://abcdef"
