"""Delete leftover test users (and, by cascade, their items) at the end of a run.

Only emails matching the strict patterns in qa.config.yaml (cleanup.test_user_email_patterns) are touched.
Superusers are never deleted, so the admin account and any hand-made users stay.
"""
import os
import re

import httpx


def cleanup_test_users(cfg: dict, dry_run: bool = False, patterns: list[str] | None = None) -> tuple[int, int]:
    """Return (matched, deleted)."""
    pats = [re.compile(p) for p in (patterns or cfg.get("cleanup", {}).get("test_user_email_patterns", []))]
    if not pats:
        return 0, 0
    base = cfg["target"]["api_url"].rstrip("/") + "/api/v1"
    admin_email = os.getenv("QA_ADMIN_EMAIL", "admin@example.com")
    admin_pw = os.getenv("QA_ADMIN_PASSWORD", "changethis")
    with httpx.Client(base_url=base, timeout=30) as c:
        tok = c.post("/login/access-token", data={"username": admin_email, "password": admin_pw})
        tok.raise_for_status()
        h = {"Authorization": f"Bearer {tok.json()['access_token']}"}
        ids, skip = [], 0
        while True:  # collect first, delete after: deleting while paging would shift the offsets
            page = c.get("/users/", params={"skip": skip, "limit": 100}, headers=h).json()
            for u in page["data"]:
                if not u["is_superuser"] and any(p.match(u["email"]) for p in pats):
                    ids.append(u["id"])
            skip += 100
            if skip >= page["count"]:
                break
        deleted = 0
        if not dry_run:
            for uid in ids:
                if c.delete(f"/users/{uid}", headers=h).status_code == 200:
                    deleted += 1
    return len(ids), deleted
