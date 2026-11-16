import uuid

import pytest
from conftest import PASSWORD


def _email():
    return f"user_{uuid.uuid4().hex[:12]}@example.com"


def _signup(api, email=None, password=PASSWORD, full_name="Test User"):
    return api.post(
        "/users/signup",
        json={"email": email or _email(), "password": password, "full_name": full_name},
    )


def _login(api, email, password):
    return api.post("/login/access-token", data={"username": email, "password": password})


@pytest.mark.tc("TC-001")
def test_tc_001_signup_valid_creates_user(api):
    email = _email()
    r = _signup(api, email=email, full_name="Alice")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == email
    assert body["id"]
    assert body["is_active"] is True
    assert body["is_superuser"] is False
    assert body["full_name"] == "Alice"
    assert "password" not in body
    assert "hashed_password" not in body


@pytest.mark.tc("TC-002")
def test_tc_002_signup_duplicate_email_rejected(api, admin_headers):
    email = _email()
    assert _signup(api, email=email).status_code == 200
    r = _signup(api, email=email)
    assert r.status_code == 400
    assert "detail" in r.json()
    lst = api.get("/users/", headers=admin_headers, params={"limit": 1000})
    assert lst.status_code == 200
    assert sum(1 for u in lst.json()["data"] if u["email"] == email) == 1


@pytest.mark.tc("TC-003")
def test_tc_003_signup_invalid_email_format(api):
    r = _signup(api, email="not-an-email")
    assert r.status_code == 422
    assert any("email" in e["loc"] for e in r.json()["detail"])


@pytest.mark.tc("TC-004")
def test_tc_004_signup_password_below_min_length(api):
    email = _email()
    r = _signup(api, email=email, password="a" * 7)
    assert r.status_code == 422
    assert _login(api, email, "a" * 7).status_code == 400


@pytest.mark.tc("TC-005")
def test_tc_005_signup_password_boundaries(api):
    assert _signup(api, password="a" * 8).status_code == 200
    assert _signup(api, password="b" * 128).status_code == 200
    assert _signup(api, password="c" * 129).status_code == 422


@pytest.mark.tc("TC-023")
def test_tc_023_get_own_profile(api, new_user):
    u = new_user()
    r = api.get("/users/me", headers=u["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == u["email"]
    assert "full_name" in body
    assert body["id"] == u["id"]


@pytest.mark.tc("TC-024")
def test_tc_024_update_own_profile(api, new_user):
    u = new_user()
    new_email = _email()
    r = api.patch("/users/me", headers=u["headers"], json={"full_name": "New Name", "email": new_email})
    assert r.status_code == 200
    assert r.json()["full_name"] == "New Name"
    assert r.json()["email"] == new_email
    me = api.get("/users/me", headers=u["headers"])
    assert me.status_code == 200
    assert me.json()["full_name"] == "New Name"
    assert me.json()["email"] == new_email


@pytest.mark.tc("TC-025")
def test_tc_025_update_own_email_to_existing(api, new_user):
    a = new_user()
    b = new_user()
    r = api.patch("/users/me", headers=a["headers"], json={"email": b["email"]})
    assert r.status_code == 409
    me = api.get("/users/me", headers=a["headers"])
    assert me.json()["email"] == a["email"]


@pytest.mark.tc("TC-026")
def test_tc_026_change_password_correct_current(api, new_user):
    u = new_user()
    new_pw = "brand-new-password-1"
    r = api.patch(
        "/users/me/password",
        headers=u["headers"],
        json={"current_password": u["password"], "new_password": new_pw},
    )
    assert r.status_code == 200
    assert "message" in r.json()
    assert _login(api, u["email"], new_pw).status_code == 200
    assert _login(api, u["email"], u["password"]).status_code == 400


@pytest.mark.tc("TC-027")
def test_tc_027_change_password_wrong_current_or_same(api, new_user):
    u = new_user()
    r1 = api.patch(
        "/users/me/password",
        headers=u["headers"],
        json={"current_password": "wrong-current-pass", "new_password": "another-new-pass-1"},
    )
    assert r1.status_code == 400
    r2 = api.patch(
        "/users/me/password",
        headers=u["headers"],
        json={"current_password": u["password"], "new_password": u["password"]},
    )
    assert r2.status_code == 400
    assert _login(api, u["email"], u["password"]).status_code == 200


@pytest.mark.tc("TC-028")
def test_tc_028_normal_user_cannot_access_admin_endpoints(api, new_user):
    a = new_user()
    b = new_user()
    h = a["headers"]
    assert api.get("/users/", headers=h).status_code == 403
    assert api.get(f"/users/{b['id']}", headers=h).status_code == 403
    assert api.patch(f"/users/{b['id']}", headers=h, json={"full_name": "Hacked"}).status_code == 403
    assert api.delete(f"/users/{b['id']}", headers=h).status_code == 403
    me = api.get("/users/me", headers=b["headers"])
    assert me.status_code == 200


@pytest.mark.tc("TC-029")
def test_tc_029_delete_own_account(api, new_user):
    u = new_user()
    r = api.delete("/users/me", headers=u["headers"])
    assert r.status_code == 200
    assert "message" in r.json()
    assert _login(api, u["email"], u["password"]).status_code == 400


@pytest.mark.tc("TC-030")
def test_tc_030_superuser_cannot_delete_self(api, admin_headers):
    r = api.delete("/users/me", headers=admin_headers)
    assert r.status_code == 403
    me = api.get("/users/me", headers=admin_headers)
    assert me.status_code == 200


@pytest.mark.tc("TC-048")
def test_tc_048_users_endpoints_reject_no_token(api):
    r1 = api.get("/users/me")
    assert r1.status_code == 401
    r2 = api.patch("/users/me", json={"full_name": "x"})
    assert r2.status_code == 401
    r3 = api.get("/users/")
    assert r3.status_code == 401
