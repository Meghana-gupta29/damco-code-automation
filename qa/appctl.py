"""Control of the app under test: sabotage branch, docker deploy, health."""
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

SABOTAGE_BRANCH = "demo/sabotage"
GIT_ID = ["-c", "user.name=QA Orchestrator", "-c", "user.email=qa-orchestrator@example.com"]


def git(repo: Path, *args, check=True) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.strip()[:500]}")
    return r.stdout.strip()


def current_branch(repo: Path) -> str:
    return git(repo, "rev-parse", "--abbrev-ref", "HEAD")


def head_sha(repo: Path) -> str:
    return git(repo, "rev-parse", "--short", "HEAD")


def app_dirty(repo: Path) -> bool:
    return bool(git(repo, "status", "--porcelain", "--", "backend", "frontend"))


def docker_bin() -> str:
    found = shutil.which("docker")
    if found:
        return found
    for base in (os.environ.get("LOCALAPPDATA", "") + r"\Programs\DockerDesktop",
                 r"C:\Program Files\Docker\Docker"):
        cand = Path(base) / "resources" / "bin" / "docker.exe"
        if cand.exists():
            return str(cand)
    raise SystemExit("docker not found. Install Docker Desktop and make sure it is running.")


def health(cfg: dict) -> bool:
    try:
        with urllib.request.urlopen(cfg["target"]["api_url"] + "/api/v1/utils/health-check/", timeout=5) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def sabotage_apply(cfg: dict) -> None:
    repo, base = cfg["_target_repo"], cfg["target"]["base_branch"]
    if app_dirty(repo):
        raise SystemExit("App has uncommitted changes in backend/ or frontend/. Commit or stash them first.")
    if git(repo, "branch", "--list", SABOTAGE_BRANCH):
        git(repo, "checkout", SABOTAGE_BRANCH)
        print(f"Branch {SABOTAGE_BRANCH} already exists; checked out.")
        return
    git(repo, "checkout", "-b", SABOTAGE_BRANCH, base)
    patches = sorted((cfg["_root"] / "sabotage").glob("*.patch"))
    for p in patches:
        git(repo, "apply", "--ignore-whitespace", str(p))
        print(f"  applied {p.name}")
    git(repo, "add", "backend", "frontend")
    git(repo, *GIT_ID, "commit", "-q", "-m", "SABOTAGE (demo): " + ", ".join(p.stem for p in patches))
    print(f"Created branch {SABOTAGE_BRANCH} from {base} with {len(patches)} deliberate bugs. HEAD={head_sha(repo)}")
    print("Next: qa app deploy")


def sabotage_revert(cfg: dict) -> None:
    repo, base = cfg["_target_repo"], cfg["target"]["base_branch"]
    if app_dirty(repo):
        raise SystemExit("App has uncommitted changes in backend/ or frontend/. Commit or stash them first.")
    git(repo, "checkout", base)
    print(f"Checked out {base}. Next: qa app deploy")


def deploy(cfg: dict) -> None:
    repo = cfg["_target_repo"]
    print(f"Deploying app branch '{current_branch(repo)}' @ {head_sha(repo)} (docker compose build backend)...")
    exe = docker_bin()
    env = {**os.environ, "PATH": str(Path(exe).parent) + os.pathsep + os.environ.get("PATH", "")}
    r = subprocess.run([exe, "compose", "up", "-d", "--build", "backend"], cwd=repo, env=env)
    if r.returncode:
        raise SystemExit("docker compose failed; is Docker Desktop running?")
    for _ in range(60):
        if health(cfg):
            print("App is healthy.")
            return
        time.sleep(2)
    raise SystemExit("App did not become healthy within 120s. Check: docker compose logs backend")


def status(cfg: dict) -> None:
    repo = cfg["_target_repo"]
    print(f"App branch: {current_branch(repo)} @ {head_sha(repo)}{' (uncommitted changes)' if app_dirty(repo) else ''}")
    print("App healthy:", health(cfg))
