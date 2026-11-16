import uuid

import pytest


def _create(api, headers, title="Item", description="desc"):
    r = api.post("/items/", headers=headers, json={"title": title, "description": description})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.tc("TC-012")
def test_tc_012_create_item_valid(api, new_user):
    u = new_user()
    r = api.post("/items/", headers=u["headers"], json={"title": "My item", "description": "My desc"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"]
    assert body["title"] == "My item"
    assert body["description"] == "My desc"
    assert body["owner_id"] == u["id"]


@pytest.mark.tc("TC-013")
def test_tc_013_create_item_without_title(api, new_user):
    u = new_user()
    r = api.post("/items/", headers=u["headers"], json={"description": "x"})
    assert r.status_code == 422
    assert any("title" in e["loc"] for e in r.json()["detail"])


@pytest.mark.tc("TC-014")
def test_tc_014_item_title_boundaries(api, new_user):
    u = new_user()
    h = u["headers"]
    assert api.post("/items/", headers=h, json={"title": ""}).status_code == 422
    assert api.post("/items/", headers=h, json={"title": "a"}).status_code == 200
    assert api.post("/items/", headers=h, json={"title": "a" * 255}).status_code == 200
    assert api.post("/items/", headers=h, json={"title": "a" * 256}).status_code == 422


@pytest.mark.tc("TC-015")
def test_tc_015_item_description_boundaries(api, new_user):
    u = new_user()
    h = u["headers"]
    assert api.post("/items/", headers=h, json={"title": "t", "description": "d" * 255}).status_code == 200
    assert api.post("/items/", headers=h, json={"title": "t", "description": "d" * 256}).status_code == 422


@pytest.mark.tc("TC-016")
def test_tc_016_items_endpoints_require_auth(api):
    item_id = uuid.uuid4()
    assert api.get("/items/").status_code == 401
    assert api.post("/items/", json={"title": "t"}).status_code == 401
    assert api.get(f"/items/{item_id}").status_code == 401
    assert api.put(f"/items/{item_id}", json={"title": "t"}).status_code == 401
    assert api.delete(f"/items/{item_id}").status_code == 401


@pytest.mark.tc("TC-017")
def test_tc_017_list_items_only_own(api, new_user):
    a = new_user()
    b = new_user()
    a1 = _create(api, a["headers"], "a1")
    a2 = _create(api, a["headers"], "a2")
    b1 = _create(api, b["headers"], "b1")
    r = api.get("/items/", headers=a["headers"])
    assert r.status_code == 200
    body = r.json()
    ids = {i["id"] for i in body["data"]}
    assert ids == {a1["id"], a2["id"]}
    assert b1["id"] not in ids
    assert body["count"] == 2


@pytest.mark.tc("TC-018")
def test_tc_018_get_item_owned_by_another_user(api, new_user):
    a = new_user()
    b = new_user()
    item = _create(api, b["headers"], "secret-title", "secret-desc")
    r = api.get(f"/items/{item['id']}", headers=a["headers"])
    assert r.status_code == 403
    body = r.json()
    assert "title" not in body
    assert "owner_id" not in body


@pytest.mark.tc("TC-019")
def test_tc_019_update_other_users_item_blocked(api, new_user):
    a = new_user()
    b = new_user()
    item = _create(api, b["headers"], "original", "orig-desc")
    r = api.put(f"/items/{item['id']}", headers=a["headers"], json={"title": "hijacked"})
    assert r.status_code == 403
    g = api.get(f"/items/{item['id']}", headers=b["headers"])
    assert g.status_code == 200
    assert g.json()["title"] == "original"
    assert g.json()["description"] == "orig-desc"


@pytest.mark.tc("TC-020")
def test_tc_020_delete_other_users_item_blocked(api, new_user):
    a = new_user()
    b = new_user()
    item = _create(api, b["headers"])
    r = api.delete(f"/items/{item['id']}", headers=a["headers"])
    assert r.status_code == 403
    g = api.get(f"/items/{item['id']}", headers=b["headers"])
    assert g.status_code == 200
    assert g.json()["id"] == item["id"]


@pytest.mark.tc("TC-021")
def test_tc_021_owner_updates_and_deletes_item(api, new_user):
    u = new_user()
    h = u["headers"]
    item = _create(api, h, "before")
    up = api.put(f"/items/{item['id']}", headers=h, json={"title": "after"})
    assert up.status_code == 200
    assert up.json()["title"] == "after"
    assert up.json()["id"] == item["id"]
    d = api.delete(f"/items/{item['id']}", headers=h)
    assert d.status_code == 200
    assert "message" in d.json()
    assert api.get(f"/items/{item['id']}", headers=h).status_code == 404


@pytest.mark.tc("TC-022")
def test_tc_022_get_item_nonexistent_or_malformed_id(api, new_user):
    u = new_user()
    h = u["headers"]
    r1 = api.get(f"/items/{uuid.uuid4()}", headers=h)
    assert r1.status_code == 404
    r2 = api.get("/items/abc", headers=h)
    assert r2.status_code == 422


@pytest.mark.tc("TC-049")
def test_tc_049_item_write_ops_reject_no_token(api, new_user):
    a = new_user()
    item = _create(api, a["headers"], "keep-me", "keep-desc")
    assert api.post("/items/", json={"title": "anon"}).status_code == 401
    assert api.put(f"/items/{item['id']}", json={"title": "changed"}).status_code == 401
    assert api.delete(f"/items/{item['id']}").status_code == 401
    g = api.get(f"/items/{item['id']}", headers=a["headers"])
    assert g.status_code == 200
    assert g.json()["title"] == "keep-me"
    assert g.json()["description"] == "keep-desc"
