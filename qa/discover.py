"""Stage 0: read the target repo and build context.json (routes -> source files).

This module map is what lets triage say *which file* a failing test points at.
"""
import re
from pathlib import Path

PREFIX_RE = re.compile(r'APIRouter\([^)]*prefix="([^"]*)"')
ROUTE_RE = re.compile(r'@router\.(get|post|put|patch|delete)\(\s*"([^"]*)"')


def discover(target_repo: Path) -> dict:
    routes_dir = target_repo / "backend" / "app" / "api" / "routes"

    endpoints = []
    for f in sorted(routes_dir.glob("*.py")):
        if f.name.startswith("__"):
            continue
        rel = f.relative_to(target_repo).as_posix()
        src = f.read_text(encoding="utf-8")
        m = PREFIX_RE.search(src)
        prefix = m.group(1) if m else ""
        for method, path in ROUTE_RE.findall(src):
            endpoints.append({"method": method.upper(), "path": f"/api/v1{prefix}{path}",
                              "module": rel})

    ui_routes = [p.relative_to(target_repo).as_posix()
                 for p in sorted((target_repo / "frontend" / "src" / "routes").rglob("*.tsx"))]
    return {
        "target_repo": str(target_repo),
        "endpoints": endpoints,
        "ui_routes": ui_routes,
        "backend_modules": ["backend/app/crud.py", "backend/app/models.py",
                            "backend/app/core/security.py", "backend/app/api/deps.py"],
    }
