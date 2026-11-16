"""Stage 3: execute suites and store normalized results in the run folder."""
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
