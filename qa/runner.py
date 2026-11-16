"""Stage 3: execute suites and store normalized results in the run folder."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run_api(cfg: dict, run, only: list[str] | None = None) -> dict:
    root: Path = cfg["_root"]
    out = run.path("results_api.json")
    cmd = [sys.executable, "-m", "pytest", "generated/api", "-p", "qa.pytest_plugin",
           "--qa-results", str(out), "-q", "--no-header", "-p", "no:cacheprovider"]
    if only:
        cmd += ["-m", " or ".join(f'tc("{t}")' for t in only)] if False else ["-k", " or ".join(t.lower().replace("-", "_") for t in only)]
    proc = subprocess.run(cmd, cwd=root, text=True, capture_output=True)
    (run.path("pytest_api.log")).write_text(proc.stdout + proc.stderr, encoding="utf-8")
    return run.read_json("results_api.json")


def _walk(suite, rows):
    for spec in suite.get("specs", []):
        title = spec["title"]
        m = re.match(r"(TC-\d+)", title)
        for t in spec.get("tests", []):
            res = t.get("results", [{}])[-1]
            status = res.get("status", "skipped")
            outcome = {"passed": "passed", "skipped": "skipped"}.get(status, "failed")
            err = None
            if outcome == "failed":
                err = (res.get("error", {}) or {}).get("message", "")[-1800:]
            rows.append({"tc": m.group(1) if m else None, "test": f"{spec['file']}::{title}",
                         "outcome": outcome, "duration_s": round(res.get("duration", 0) / 1000, 3),
                         "error": err, "phase": "call",
                         "attachments": [a.get("path") for a in res.get("attachments", []) if a.get("path")]})
    for s in suite.get("suites", []):
        _walk(s, rows)


def run_ui(cfg: dict, run, only: list[str] | None = None) -> dict:
    root: Path = cfg["_root"]
    raw = run.path("results_ui_raw.json")
    env = {**os.environ, "QA_UI_RESULTS": str(raw)}
    npx = shutil.which("npx") or "npx"
    cmd = [npx, "playwright", "test", "--output", str(run.path("ui-artifacts"))]
    if only:
        cmd += ["--grep", "|".join(only)]
    proc = subprocess.run(cmd, cwd=root, env=env, text=True, capture_output=True, encoding="utf-8")
    run.path("playwright_ui.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    rows = []
    if raw.exists():
        data = json.loads(raw.read_text(encoding="utf-8"))
        for s in data.get("suites", []):
            _walk(s, rows)
    result = {"suite": "ui", "rows": rows}
    run.write_json("results_ui.json", result)
    return result
