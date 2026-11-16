"""Gate 2 (human decides: fix the CODE or update the TEST) and the two fix paths."""
import difflib
import getpass
import json
import re
from datetime import datetime
from pathlib import Path

from .appctl import GIT_ID, git
from .generate import FILE_RE
from .llm import get_provider
from .triage import app_diff, test_source

SUMMARY_RE = re.compile(r"=== SUMMARY ===\n(.*?)\n=== END ===", re.S)
CODE_PREFIXES = ("backend/", "frontend/src/")


def _load(run):
    return run.read_json("defects.json") if run.path("defects.json").exists() else []


def decide(cfg, run, defect_id=None, choice=None) -> dict:
    defects = _load(run)
    if not defects:
        raise SystemExit("No defects in this run. Run: qa triage")
    decisions = run.read_json("decisions.json") if run.path("decisions.json").exists() else {}
    for d in defects:
        if defect_id and d["id"] != defect_id:
            continue
        if d["status"] != "Open" and not defect_id:
            continue
        print(f"\n{d['id']} [{d['severity']}] {d['title']}")
        print(f"  tests:    {', '.join(d['tcs'])}")
        print(f"  suspect:  {d['suspect_module']}  {d.get('suspect_detail', '')}")
        print(f"  AI view:  {d['classification']} -> {d['recommendation']} (confidence {d.get('confidence', 'n/a')})")
        print(f"  why:      {d.get('rationale') or d['root_cause']}")
        c = choice
        while c not in ("code", "test", "skip"):
            a = input("  Your decision: [c] fix the CODE   [t] update the TEST   [s] skip  > ").strip().lower()
            c = {"c": "code", "t": "test", "s": "skip"}.get(a)
        decisions[d["id"]] = {"choice": c, "by": getpass.getuser(), "ai_recommendation": d["recommendation"],
                              "at": datetime.now().isoformat(timespec="seconds")}
        if c != "skip":
            d["status"] = "In Progress"
            d["resolution"] = "fix code" if c == "code" else "update test"
    run.write_json("decisions.json", decisions)
    from .triage import save_defects
    save_defects(run, defects)
    from .report import write_report
    write_report(run, cfg)  # keep report/dashboard in sync with defect statuses
    print("\nDecisions recorded in decisions.json. Next: qa fix")
    return decisions


def _confirm(prompt: str, yes: bool) -> bool:
    return yes or input(prompt + " [y/N] ").strip().lower() == "y"


def fix_code(cfg, run, d, yes) -> bool:
    repo, root = cfg["_target_repo"], cfg["_root"]
    diff, changed = app_diff(repo, d.get("regression_from", ""))
    files = list(dict.fromkeys([d["suspect_module"]] + [c for c in changed if c.endswith((".py", ".ts", ".tsx"))]))
    src = "\n\n".join(f"### {p}\n{(repo / p).read_text(encoding='utf-8')}" for p in files if (repo / p).is_file())
    task = (f"## DEFECT\n{json.dumps({k: v for k, v in d.items() if k != 'evidence'}, indent=1)}\n\n"
            f"## REGRESSION DIFF\n{diff or '(none)'}\n\n## SOURCE\n{src}")
    print(f"[{d['id']}] fixer agent working on {d['suspect_module']} ...")
    text = get_provider(cfg).run_agent("fixer", task, root)
    blocks = FILE_RE.findall(text)
    if not blocks:
        raise RuntimeError("Fixer returned no files: " + text[:300])
    originals = {}
    for path, body in blocks:
        path = path.strip().replace("\\", "/")
        if not path.startswith(CODE_PREFIXES) or ".." in path:
            raise RuntimeError(f"Fixer tried to write outside the app code area: {path}")
        body = re.sub(r"^```\w*\n|\n```$", "", body.strip()) + "\n"
        if path.endswith(".py"):
            compile(body, path, "exec")  # reject syntactically broken fixes
        target = repo / path
        originals[path] = target.read_text(encoding="utf-8")
        target.write_text(body, encoding="utf-8", newline="\n")
    m = SUMMARY_RE.search(text)
    summary = m.group(1).strip() if m else "fix"
    print(f"\nProposed code fix: {summary}\n")
    print(git(repo, "diff", "--", *originals.keys()))
    if not _confirm("\nApply this fix to the app and commit it on the current branch?", yes):
        for p, old in originals.items():
            (repo / p).write_text(old, encoding="utf-8", newline="\n")
        print("Fix discarded.")
        return False
    git(repo, "add", *originals.keys())
    git(repo, *GIT_ID, "commit", "-q", "-m", f"fix({d['id']}): {summary}\n\nTests: {', '.join(d['tcs'])}")
    return True


def _tc_ids(text: str) -> set[str]:
    return set(re.findall(r'(?:mark\.tc\("|test\(\s*["`\'])(TC-\d+)', text))


def fix_test(cfg, run, d, yes) -> bool:
    repo, root = cfg["_target_repo"], cfg["_root"]
    diff, _ = app_diff(repo, d.get("regression_from", ""))
    files = {}
    for tc in d["tcs"]:
        path, _src = test_source(root, tc)
        if path:
            files[path] = (root / path).read_text(encoding="utf-8")
    plan = {c["id"]: c for c in run.read_json("test_cases.json") if c["id"] in d["tcs"]}
    task = (f"## DEFECT (human decided: the TEST is outdated, the app is right)\n"
            f"{json.dumps({k: v for k, v in d.items() if k != 'evidence'}, indent=1)}\n\n"
            f"## PLAN ENTRIES\n{json.dumps(plan, indent=1)}\n\n## APP DIFF (intended behavior)\n{diff or '(none)'}\n\n"
            "## TEST FILES\n" + "\n\n".join(f"### {p}\n{s}" for p, s in files.items()))
    print(f"[{d['id']}] test-updater agent working on {', '.join(files)} ...")
    text = get_provider(cfg).run_agent("test-updater", task, root)
    new_files, plan_update = {}, {}
    for path, body in FILE_RE.findall(text):
        path = path.strip().replace("\\", "/")
        body = re.sub(r"^```\w*\n|\n```$", "", body.strip()) + "\n"
        if path == "plan_update.json":
            plan_update = json.loads(body)
        elif path in files:
            new_files[path] = body
        else:
            raise RuntimeError(f"Test-updater tried to write an unexpected file: {path}")
    if not new_files:
        raise RuntimeError("Test-updater returned no test files: " + text[:300])
    for p, body in new_files.items():
        if _tc_ids(body) != _tc_ids(files[p]):
            raise RuntimeError(f"Test-updater changed the set of test cases in {p}; refusing.")
        if p.endswith(".py"):
            compile(body, p, "exec")
    summary = (SUMMARY_RE.search(text).group(1) if SUMMARY_RE.search(text) else "test updated")
    print(f"\nProposed test change: {summary}\n")
    for p, body in new_files.items():
        print("".join(difflib.unified_diff(files[p].splitlines(True), body.splitlines(True), p + " (before)", p + " (after)")))
    if plan_update:
        print("Plan amendment:", json.dumps(plan_update, indent=1))
    if not _confirm("\nApply this test update (and amend the approved plan)?", yes):
        print("Test update discarded.")
        return False
    for p, body in new_files.items():
        (root / p).write_text(body, encoding="utf-8", newline="\n")
    if plan_update:
        cases = run.read_json("test_cases.json")
        for c in cases:
            c.update(plan_update.get(c["id"], {}))
        run.write_json("test_cases.json", cases)
        run.reapprove_amended(getpass.getuser(), f"{d['id']}: {summary}", d["tcs"])
    return True


def apply_fixes(cfg, run, yes=False) -> None:
    if not run.path("decisions.json").exists():
        raise SystemExit("No decisions yet. Run: qa decide")
    decisions = run.read_json("decisions.json")
    defects = _load(run)
    for d in defects:
        dec = decisions.get(d["id"], {}).get("choice")
        if d["status"] != "In Progress" or dec not in ("code", "test"):
            continue
        ok = fix_code(cfg, run, d, yes) if dec == "code" else fix_test(cfg, run, d, yes)
        if ok:
            d["status"] = "Fixed (pending verification)"
    from .triage import save_defects
    save_defects(run, defects)
    from .report import write_report
    write_report(run, cfg)
    left = [d["id"] for d in defects if d["status"] == "In Progress"]
    print("\nDone." + (f" Not applied: {', '.join(left)}." if left else ""))
    print("Next: qa app deploy   (if code was fixed), then: qa run --label fixed")


def carry_defects(prev, new) -> None:
    """Carry defects from the previous run; close those whose tests now pass."""
    if not prev.path("defects.json").exists():
        return
    outcome = {}
    for suite in ("api", "ui"):
        f = new.path(f"results_{suite}.json")
        if f.exists():
            outcome.update({r["tc"]: r["outcome"] for r in json.loads(f.read_text(encoding="utf-8"))["rows"]})
    out = []
    for d in json.loads(prev.path("defects.json").read_text(encoding="utf-8")):
        if d["status"] == "Closed":
            continue
        ok = all(outcome.get(t) == "passed" for t in d["tcs"])
        d = {**d, "status": "Closed" if ok else "Open", "run_id": new.id,
             "verified_in": new.id if ok else None, "first_seen_in": d.get("first_seen_in", d["run_id"])}
        out.append(d)
    from .triage import save_defects
    save_defects(new, out)
