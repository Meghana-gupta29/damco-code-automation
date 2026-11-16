import uuid

import pytest
from conftest import PASSWORD


def _signup(api):
    email = f"login_{uuid.uuid4().hex[:12]}@example.com"
    r = api.post("/users/signup", json={"email": email, "password": PASSWORD, "full_name": "Login User"})
    assert r.status_code == 200, r.text
    return email


def _token(api, email, password):
    return api.post("/login/access-token", data={"username": email, "password": password})


@pytest.mark.tc("TC-006")
def test_tc_006_login_valid_credentials_returns_token(api):
    email = _signup(api)
    r = _token(api, email, PASSWORD)
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


@pytest.mark.tc("TC-007")
def test_tc_007_login_wrong_password(api):
    email = _signup(api)
    r = _token(api, email, "definitely-wrong-password")
    assert r.status_code == 400
    assert "access_token" not in r.json()


@pytest.mark.tc("TC-008")
def test_tc_008_login_non_existent_user(api):
    email = _signup(api)
    wrong = _token(api, email, "definitely-wrong-password")
    ghost = _token(api, f"ghost_{uuid.uuid4().hex[:12]}@example.com", PASSWORD)
    assert ghost.status_code == 400
    assert ghost.json() == wrong.json()


@pytest.mark.tc("TC-009")
def test_tc_009_login_missing_form_fields(api):
    r = api.post("/login/access-token", data={})
    assert r.status_code == 422
    locs = [tuple(e["loc"]) for e in r.json()["detail"]]
    assert ("body", "username") in locs
    assert ("body", "password") in locs


@pytest.mark.tc("TC-011")
def test_tc_011_tampered_jwt_rejected(api):
    email = _signup(api)
    token = _token(api, email, PASSWORD).json()["access_token"]
    head, payload, _sig = token.split(".")
    tampered = f"{head}.{payload}.invalidsignatureinvalidsignature"
    r = api.get("/users/me", headers={"Authorization": f"Bearer {tampered}"})
    assert r.status_code == 403
