"""reset-demo: return everything to the pre-recording state."""
import json
import shutil
import subprocess
import urllib.request

from . import appctl
from .appctl import SABOTAGE_BRANCH, git

RESULT_FILES = ["results_api.json", "results_ui.json", "results_ui_raw.json", "summary.json", "meta.json",
                "defects.json", "decisions.json", "report.html", "pytest_api.log", "playwright_ui.log"]


def _feature_branch(cfg: dict) -> str:
    return json.loads((cfg["_root"] / "features" / "feature.json").read_text(encoding="utf-8"))["branch"]


def _close_feature_pr(cfg: dict) -> None:
    """Close the demo PR and delete its remote branch (only the branch this tool created)."""
    gh = shutil.which("gh")
    if not gh:
        return
    fork, br = cfg["target"]["fork_repo"], _feature_branch(cfg)
    r = subprocess.run([gh, "pr", "list", "--repo", fork, "--head", br, "--state", "open", "--json", "number"],
                       capture_output=True, text=True, encoding="utf-8")
    for pr in json.loads(r.stdout or "[]"):
        subprocess.run([gh, "pr", "close", str(pr["number"]), "--repo", fork, "--delete-branch"],
                       capture_output=True, text=True, encoding="utf-8")
        print(f"Closed demo PR #{pr['number']} and deleted remote branch {br}.")
    git(cfg["_target_repo"], "push", "origin", "--delete", br, check=False)
    git(cfg["_target_repo"], "fetch", "--prune", "origin", check=False)


def reset_demo(cfg: dict, deploy: bool) -> None:
    root, repo = cfg["_root"], cfg["_target_repo"]
    runs_dir = root / cfg["paths"]["runs_dir"]
    runs = sorted(p for p in runs_dir.glob("run-*") if p.is_dir())
    plan_run = next((r for r in runs if (r / "approved.json").exists()), None)
    if plan_run is None:
        raise SystemExit("No planned run found; nothing to reset.")
    for r in runs:
        if r != plan_run:
            shutil.rmtree(r)
    for f in RESULT_FILES:
        (plan_run / f).unlink(missing_ok=True)
    for d in ("defects", "ui-artifacts"):
        shutil.rmtree(plan_run / d, ignore_errors=True)
    # restore tests + plan to the committed (approved) state in case a test update was applied
    git(root, "checkout", "--", "generated", f"{runs_dir.name}/{plan_run.name}/test_cases.json",
        f"{runs_dir.name}/{plan_run.name}/approved.json", check=False)
    git(root, "clean", "-fdq", "--", "generated")  # remove tests generated for the demo PR
    (root / "dashboard" / "index.html").unlink(missing_ok=True)
    _close_feature_pr(cfg)
    try:
        req = urllib.request.Request(cfg["email"]["inbox_url"] + "/api/v1/messages", method="DELETE")
        urllib.request.urlopen(req, timeout=5).read()
        print("Mailpit inbox cleared.")
    except Exception as e:  # noqa: BLE001
        print("Could not clear Mailpit (is it running?):", e)
    if appctl.current_branch(repo) != cfg["target"]["base_branch"]:
        git(repo, "checkout", cfg["target"]["base_branch"])
    for br in (SABOTAGE_BRANCH, _feature_branch(cfg)):
        if git(repo, "branch", "--list", br):
            git(repo, "branch", "-D", br)
    print(f"Reset done. Plan run kept: {plan_run.name}. App on {cfg['target']['base_branch']}.")
    if deploy:
        appctl.deploy(cfg)
    else:
        print("Run `qa app deploy` to rebuild the app from the base branch.")
