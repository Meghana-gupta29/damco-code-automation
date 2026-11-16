"""Developer feature + PR, and the QA agent's reaction: PR -> impact analysis -> plan delta (Gate 1)."""
import json
import re
import shutil
import subprocess
from pathlib import Path

from .appctl import GIT_ID, app_dirty, current_branch, git, head_sha
from .discover import discover
from .llm import get_provider
from .state import Run, new_run_id

SCHEMA = {"type": "object", "required": ["impact_summary", "risk", "affected_modules", "new_cases"],
          "properties": {"new_cases": {"type": "array", "items": {"type": "object",
                         "required": ["title", "layer", "type", "priority", "module", "steps", "expected"]}}}}


def gh(*args, check=True) -> str:
    exe = shutil.which("gh")
    if not exe:
        raise SystemExit("GitHub CLI (gh) not found. Install it and run `gh auth login`.")
    r = subprocess.run([exe, *args], capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode:
        raise SystemExit(f"gh {' '.join(args[:3])} failed: {r.stderr.strip()[:500]}")
    return r.stdout


def feature_apply(cfg: dict, open_pr: bool) -> None:
    """Play the developer: branch + commit the feature; optionally push and open a real PR on the fork."""
    repo, base = cfg["_target_repo"], cfg["target"]["base_branch"]
    meta = json.loads((cfg["_root"] / "features" / "feature.json").read_text(encoding="utf-8"))
    branch = meta["branch"]
    if app_dirty(repo):
        raise SystemExit("App has uncommitted changes in backend/ or frontend/. Commit or stash them first.")
    if git(repo, "branch", "--list", branch):
        git(repo, "checkout", branch)
        print(f"Branch {branch} already exists; checked out.")
    else:
        git(repo, "checkout", "-b", branch, base)
        for p in sorted((cfg["_root"] / "features").glob("*.patch")):
            git(repo, "apply", "--ignore-whitespace", str(p))
            print(f"  applied {p.name}")
        git(repo, "add", "backend", "frontend")
        git(repo, *GIT_ID, "commit", "-q", "-m", meta["commit_message"])
        print(f"Created branch {branch} from {base}. HEAD={head_sha(repo)}")
    if open_pr:
        fork = cfg["target"]["fork_repo"]
        git(repo, "push", "-u", "origin", branch)
        existing = json.loads(gh("pr", "list", "--repo", fork, "--head", branch, "--state", "open",
                                 "--json", "number,url"))
        if existing:
            print(f"PR already open: {existing[0]['url']}")
        else:
            url = gh("pr", "create", "--repo", fork, "--base", base, "--head", branch,
                     "--title", meta["pr_title"], "--body", meta["pr_body"]).strip()
            print(f"Pull request opened: {url}")
        print("Next: qa pr-sync --pr <number>")
    else:
        print(f"Next: qa pr-sync --branch {branch}")


def _next_id(cases: list[dict]) -> int:
    return max(int(c["id"].split("-")[1]) for c in cases) + 1


def pr_sync(cfg: dict, pr: int | None, branch: str | None, max_new: int) -> None:
    repo, root, base = cfg["_target_repo"], cfg["_root"], cfg["target"]["base_branch"]
    fork = cfg["target"]["fork_repo"]
    if app_dirty(repo):
        raise SystemExit("App has uncommitted changes in backend/ or frontend/. Commit or stash them first.")
    if pr:
        info = json.loads(gh("pr", "view", str(pr), "--repo", fork, "--json", "number,title,body,headRefName,url"))
        diff = gh("pr", "diff", str(pr), "--repo", fork)
        head = info["headRefName"]
        git(repo, "fetch", "origin", head)
        git(repo, "checkout", "-B", head, "FETCH_HEAD")
    elif branch:
        head = branch
        git(repo, "checkout", head)
        info = {"number": 0, "title": git(repo, "log", "-1", "--format=%s"), "body": git(repo, "log", "-1", "--format=%b"),
                "url": f"local branch {head}", "headRefName": head}
        diff = git(repo, "diff", f"{base}...{head}", "--", "backend", "frontend")
    else:
        raise SystemExit("Give --pr <number> or --branch <name>")
    changed = git(repo, "diff", "--name-only", f"{base}...{head}", "--", "backend", "frontend").split()
    print(f"Change under test: {info['title']}  ({info['url']})")
    print(f"App checked out: {head} @ {head_sha(repo)}; {len(changed)} changed file(s): {', '.join(changed)}")

    runs_dir = root / cfg["paths"]["runs_dir"]
    prev = Run.latest(runs_dir)
    cases = prev.read_json("test_cases.json")
    run = Run(runs_dir, new_run_id())
    run.write_json("context.json", discover(repo))
    sources = "\n\n".join(f"### {p}\n{(repo / p).read_text(encoding='utf-8')}" for p in changed
                          if (repo / p).is_file() and p.endswith((".py", ".ts", ".tsx")))[:60000]
    plan_view = [{k: c[k] for k in ("id", "title", "layer", "module")} for c in cases]
    task = (f"Limit: at most {max_new} new case(s) per layer (API and UI).\n\n## PR\nTitle: {info['title']}\n"
            f"Description:\n{info['body']}\n\n## DIFF\n{diff[:30000]}\n\n## CHANGED SOURCE\n{sources}\n\n"
            f"## CURRENT APPROVED PLAN\n{json.dumps(plan_view, indent=0)}")
    print("QA agent analysing the change...")
    out = get_provider(cfg).run_agent_json("change-analyst", task, root, SCHEMA)

    kept, counts = [], {"API": 0, "UI": 0}
    for c in out["new_cases"]:
        if c["layer"] in counts and counts[c["layer"]] < max_new:
            counts[c["layer"]] += 1
            kept.append(c)
    nid = _next_id(cases)
    origin = {"pr": info["number"], "title": info["title"], "url": info["url"]}
    for c in kept:
        c["id"] = f"TC-{nid:03d}"
        nid += 1
        c["origin"] = origin
    run.write_json("test_cases.json", cases + kept)   # NOT approved: Gate 1 applies to the delta too
    slug = re.sub(r"[^a-z0-9]+", "_", head.split("/")[-1].lower()).strip("_")
    tag = f"pr{info['number']}_{slug}" if info["number"] else f"branch_{slug}"
    run.write_json("pr_context.json", {**info, "branch": head, "head_sha": head_sha(repo), "changed_files": changed,
                                        "tag": tag})
    run.write_json("plan_delta.json", {**out, "new_cases": kept})

    print(f"\nImpact ({out['risk']} risk): {out['impact_summary']}")
    print("Affected modules:", ", ".join(out["affected_modules"]))
    for r in out.get("cases_to_review", []):
        print(f"  review existing {r['tc']}: {r['reason']}")
    print("\nProposed NEW test cases (need your approval):")
    for c in kept:
        print(f"  {c['id']} [{c['layer']}/{c['type']}/{c['priority']}] {c['title']}\n      module: {c['module']}\n"
              f"      expected: {c['expected']}")
    print(f"\nReview/edit: {run.path('test_cases.json')}  (details: plan_delta.json)\nThen: qa approve plan")
