"""Stage 4: classify failures into defects, name the suspect module, write defect reports."""
import json
import re
from pathlib import Path

from .appctl import git
from .llm import get_provider
from .report import load_history, write_report

SCHEMA = {
    "type": "array",
    "items": {"type": "object",
              "required": ["title", "tcs", "classification", "recommendation", "severity", "suspect_module",
                           "root_cause", "steps", "expected", "actual"]},
}


def test_source(root: Path, tc: str):
    """Return (relative file, source text) of the test implementing case `tc`."""
    files = [f for f in (root / "generated").rglob("*") if f.suffix in (".py", ".ts") and f.name != "conftest.py"]
    pat = re.compile(r'(@pytest\.mark\.tc\("%s"\)|test\(\s*["`\']%s\b)' % (tc, tc))
    for f in files:
        src = f.read_text(encoding="utf-8")
        m = pat.search(src)
        if not m:
            continue
        nxt = re.search(r'\n(@pytest\.mark\.tc\(|test\(\s*["`\']TC-)', src[m.end():])
        end = m.end() + nxt.start() if nxt else len(src)
        return f.relative_to(root).as_posix(), src[m.start():end]
    return None, ""


def last_green_sha(runs_dir: Path, current_id: str) -> str:
    for s in reversed(load_history(runs_dir)):
        if s["run_id"] != current_id and s["verdict"] == "Go" and s.get("app_git"):
            return s["app_git"].split("+")[0]
    return ""


def app_diff(repo: Path, sha: str) -> tuple[str, list[str]]:
    if not sha:
        return "", []
    diff = git(repo, "diff", sha, "--", "backend", "frontend", check=False)
    names = git(repo, "diff", "--name-only", sha, "--", "backend", "frontend", check=False).split()
    return diff[:20000], names


def run_triage(cfg: dict, run) -> list[dict]:
    root, repo = cfg["_root"], cfg["_target_repo"]
    summary = run.read_json("summary.json")
    failures = summary["failures"]
    if not failures:
        run.write_json("defects.json", [])
        print("No failures; nothing to triage.")
        return []

    sha = last_green_sha(root / cfg["paths"]["runs_dir"], run.id)
    diff, changed = app_diff(repo, sha)
    plan = {c["id"]: c for c in run.read_json("test_cases.json")}
    ui_rows = {r["tc"]: r for r in (run.read_json("results_ui.json")["rows"] if run.path("results_ui.json").exists() else [])}

    fail_ctx = []
    for f in failures:
        path, src = test_source(root, f["tc"])
        fail_ctx.append({"tc": f["tc"], "suite": f["suite"], "priority": f["priority"],
                         "plan_entry": plan.get(f["tc"]), "error": f["error"], "test_file": path,
                         "test_source": src})
    suspects = list(dict.fromkeys(changed + [f["module"] for f in failures]))
    sources = "\n\n".join(f"### {p}\n{(repo / p).read_text(encoding='utf-8')}" for p in suspects
                          if (repo / p).is_file() and p.endswith((".py", ".tsx", ".ts")))[:60000]
    task = (f"Triage these {len(failures)} failing tests.\n\n## FAILURES\n{json.dumps(fail_ctx, indent=1)}\n\n"
            f"## APP DIFF since last green build ({sha or 'unknown'} -> current)\n{diff or '(not available)'}\n\n"
            f"## SUSPECT SOURCE FILES\n{sources}")
    print(f"Triaging {len(failures)} failure(s); regression diff against {sha or 'n/a'}: {len(changed)} changed file(s)...")
    items = get_provider(cfg).run_agent_json("triager", task, root, SCHEMA)

    covered = {t for d in items for t in d["tcs"]}
    for f in failures:  # never silently drop a failure
        if f["tc"] not in covered:
            items.append({"title": f"Unclassified failure in {f['tc']}: {f['title']}", "tcs": [f["tc"]],
                          "classification": "unclassified", "recommendation": "investigate", "severity": "Sev3",
                          "suspect_module": f["module"], "root_cause": "Not covered by triage output.",
                          "steps": [], "expected": "", "actual": f["error"][-300:], "confidence": "low"})
    defects = []
    for i, d in enumerate(items, 1):
        d.update({"id": f"DEF-{i:03d}", "status": "Open", "run_id": run.id, "regression_from": sha,
                  "evidence": [{"tc": t, "error": next((f["error"] for f in failures if f["tc"] == t), ""),
                                "attachments": ui_rows.get(t, {}).get("attachments", [])} for t in d["tcs"]]})
        defects.append(d)
    save_defects(run, defects)
    print_defects(defects)
    return defects


def save_defects(run, defects: list[dict]) -> None:
    run.write_json("defects.json", defects)
    out = run.path("defects")
    out.mkdir(exist_ok=True)
    for d in defects:
        steps = "\n".join(f"{n}. {s}" for n, s in enumerate(d.get("steps", []), 1))
        ev = "\n\n".join(f"**{e['tc']}**\n```\n{(e['error'] or '')[-900:]}\n```\n" +
                         "".join(f"Screenshot/trace: `{a}`\n" for a in e["attachments"]) for e in d["evidence"])
        out.joinpath(f"{d['id']}.md").write_text(
            f"# {d['id']}: {d['title']}\n\n"
            f"- **Severity:** {d['severity']}\n- **Status:** {d['status']}\n"
            f"- **Classification (AI):** {d['classification']} (confidence: {d.get('confidence', 'n/a')})\n"
            f"- **AI recommendation:** {d['recommendation']}\n"
            f"- **Failing tests:** {', '.join(d['tcs'])}\n"
            f"- **Suspect module:** `{d['suspect_module']}` {d.get('suspect_detail', '')}\n"
            f"- **Regression since app commit:** {d.get('regression_from') or 'n/a'}\n"
            f"- **Run:** {d['run_id']}\n\n"
            f"## Root cause (AI)\n{d['root_cause']}\n\n## Why this classification\n{d.get('rationale', '')}\n\n"
            f"## Steps to reproduce\n{steps}\n\n## Expected\n{d['expected']}\n\n## Actual\n{d['actual']}\n\n"
            f"## Evidence\n{ev}\n", encoding="utf-8")


def print_defects(defects: list[dict]) -> None:
    print()
    for d in defects:
        print(f"{d['id']} [{d['severity']}] {d['title']}")
        print(f"    tests: {', '.join(d['tcs'])}")
        print(f"    suspect: {d['suspect_module']}  {d.get('suspect_detail', '')}")
        print(f"    AI says: {d['classification']} -> {d['recommendation']} (confidence {d.get('confidence', 'n/a')})")
        print(f"    why: {d.get('rationale') or d['root_cause']}")
    print()


def triage_and_report(cfg: dict, run) -> None:
    run_triage(cfg, run)
    write_report(run, cfg)
    print(f"Defect reports: {run.path('defects')}   Report: {run.path('report.html')}")
