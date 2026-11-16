import uuid

import pytest


@pytest.mark.tc("TC-050")
def test_tc_050_search_items_case_insensitive_and_scoped_to_owner(api, new_user):
    a = new_user()
    b = new_user()
    uniq = uuid.uuid4().hex[:10]

    apple_title = f"{uniq}-Apple Pie"
    banana_title = f"{uniq}-Banana Bread"
    b_apple_title = f"{uniq}-apple Tart"

    r = api.post("/items/", json={"title": apple_title}, headers=a["headers"])
    assert r.status_code == 200, r.text
    r = api.post("/items/", json={"title": banana_title}, headers=a["headers"])
    assert r.status_code == 200, r.text
    r = api.post("/items/", json={"title": b_apple_title}, headers=b["headers"])
    assert r.status_code == 200, r.text

    r = api.get("/items/", params={"search": f"{uniq}-APPLE"}, headers=a["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert "data" in body and "count" in body
    assert body["count"] == 1
    assert len(body["data"]) == 1

    item = body["data"][0]
    assert item["title"] == apple_title
    assert item["owner_id"] == a["id"]
    assert "id" in item
