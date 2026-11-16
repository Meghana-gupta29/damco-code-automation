"""Shared fixtures for generated API tests (hand-written, not agent-written)."""
import os
import uuid

import httpx
import pytest

BASE = os.getenv("QA_API_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE}/api/v1"
ADMIN_EMAIL = os.getenv("QA_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("QA_ADMIN_PASSWORD", "changethis")
PASSWORD = "Qa-Pass-12345"


@pytest.fixture(scope="session")
def api():
    """httpx client rooted at /api/v1 (use paths like '/items/')."""
    with httpx.Client(base_url=API, timeout=20, follow_redirects=True) as c:
        yield c


def login(client, email, password):
    return client.post("/login/access-token", data={"username": email, "password": password})


@pytest.fixture(scope="session")
def admin_headers(api):
    r = login(api, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def new_user(api):
    """Factory: creates a unique user via /users/signup and logs in.
    Returns dict(email, password, id, headers). Users are deleted on teardown."""
    created = []

    def _make(password=PASSWORD, full_name="QA User"):
        email = f"qa_{uuid.uuid4().hex[:12]}@example.com"
        r = api.post("/users/signup", json={"email": email, "password": password, "full_name": full_name})
        assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
        tok = login(api, email, password)
        assert tok.status_code == 200, f"login failed: {tok.status_code} {tok.text}"
        headers = {"Authorization": f"Bearer {tok.json()['access_token']}"}
        u = {"email": email, "password": password, "id": r.json()["id"], "headers": headers}
        created.append(u)
        return u

    yield _make
    admin = login(api, ADMIN_EMAIL, ADMIN_PASSWORD)
    if admin.status_code == 200:
        h = {"Authorization": f"Bearer {admin.json()['access_token']}"}
        for u in created:
            api.delete(f"/users/{u['id']}", headers=h)
