"""Stage 6: summary + verdict + HTML report/dashboard (stdlib only, self-contained HTML)."""
import html
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

CSS = """
body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f4f6f8;color:#1c2733}
.wrap{max-width:980px;margin:0 auto;padding:24px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:26px 0 8px}
.muted{color:#64748b;font-size:13px}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin-top:12px}
.verdict{border-radius:8px;padding:16px 20px;color:#fff;margin-top:14px}
.v-Go{background:#16803c}.v-No-Go{background:#b42318}.v-Go-with-risks{background:#b45309}
.verdict b{font-size:22px}
table{border-collapse:collapse;width:100%;font-size:13px;background:#fff}
th,td{border:1px solid #e2e8f0;padding:6px 9px;text-align:left;vertical-align:top}
th{background:#f1f5f9}
.pass{color:#16803c;font-weight:600}.fail{color:#b42318;font-weight:600}.skip{color:#b45309;font-weight:600}
pre{background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;font-size:12px;white-space:pre-wrap;word-break:break-word}
.bar td{border:none;padding:0 2px;text-align:center;font-size:11px}
code{background:#eef2f6;padding:1px 4px;border-radius:3px;font-size:12px}
"""


def _folder(module: str) -> str:
    return module.rsplit("/", 1)[0] if "/" in module else "."


def build_summary(run, cfg: dict) -> dict:
    cases = {c["id"]: c for c in run.read_json("test_cases.json")}
    meta = run.read_json("meta.json") if run.path("meta.json").exists() else {}
    rows = []
    suites = {}
    for suite in ("api", "ui"):
        f = run.path(f"results_{suite}.json")
        if not f.exists():
            continue
        data = json.loads(f.read_text(encoding="utf-8"))["rows"]
        for r in data:
            c = cases.get(r["tc"], {})
            rows.append({**r, "suite": suite, "title": c.get("title", r["test"]),
                         "priority": c.get("priority", "P3"), "module": c.get("module", "unknown"),
                         "type": c.get("type", "")})
        count = lambda o, d=data: sum(x["outcome"] == o for x in d)  # noqa: E731
        suites[suite] = {"total": len(data), "passed": count("passed"), "failed": count("failed"),
                         "skipped": count("skipped"),
                         "duration_s": round(sum(x["duration_s"] for x in data), 1)}
    total = sum(s["total"] for s in suites.values())
    passed = sum(s["passed"] for s in suites.values())
    failed = sum(s["failed"] for s in suites.values())
    skipped = sum(s["skipped"] for s in suites.values())

    modules = {}
    for r in rows:
        m = modules.setdefault(r["module"], {"module": r["module"], "folder": _folder(r["module"]),
                                             "tests": 0, "passed": 0, "failed": 0, "tcs": []})
        m["tests"] += 1
        m["passed"] += r["outcome"] == "passed"
        m["failed"] += r["outcome"] == "failed"
        m["tcs"].append(r["tc"])
    failures = [{k: r[k] for k in ("tc", "title", "suite", "priority", "module", "error")}
                for r in rows if r["outcome"] == "failed"]
    defects = json.loads(run.path("defects.json").read_text(encoding="utf-8")) \
        if run.path("defects.json").exists() else []

    pass_rate = round(100 * passed / total, 1) if total else 0.0
    verdict, reasons = _verdict(pass_rate, failures, skipped, defects)
    change, new_cases = None, []
    if run.path("pr_context.json").exists():
        pc = run.read_json("pr_context.json")
        delta = run.read_json("plan_delta.json") if run.path("plan_delta.json").exists() else {}
        change = {"title": pc["title"], "url": pc["url"], "branch": pc["branch"],
                  "changed_files": pc["changed_files"], "impact": delta.get("impact_summary", ""),
                  "risk": delta.get("risk", "")}
        outcome = {r["tc"]: r["outcome"] for r in rows}
        new_cases = [{"id": c["id"], "title": c["title"], "layer": c["layer"], "module": c["module"],
                      "outcome": outcome.get(c["id"], "not run")} for c in cases.values() if c.get("origin")]
    return {
        "change": change, "new_cases": new_cases,
        "run_id": run.id, "label": meta.get("label", ""), "when": meta.get("started", ""),
        "app_git": meta.get("app_git", ""), "suites": suites,
        "totals": {"total": total, "passed": passed, "failed": failed, "skipped": skipped,
                   "pass_rate": pass_rate},
        "modules": sorted(modules.values(), key=lambda m: m["module"]),
        "failures": failures, "defects": defects, "verdict": verdict, "reasons": reasons,
        "rows": [{k: r[k] for k in ("tc", "title", "suite", "outcome", "priority", "module", "duration_s")}
                 for r in rows],
    }


def _verdict(pass_rate, failures, skipped, defects):
    reasons = []
    p1 = [f for f in failures if f["priority"] == "P1"]
    sev_open = [d for d in defects if d.get("severity") in ("Sev1", "Sev2") and d.get("status") != "Closed"]
    if p1:
        reasons.append(f"{len(p1)} P1 test(s) failing: " + ", ".join(f["tc"] for f in p1))
    if sev_open:
        reasons.append(f"{len(sev_open)} open Sev1/Sev2 defect(s)")
    if pass_rate < 90:
        reasons.append(f"pass rate {pass_rate}% is below the 90% threshold")
    if p1 or sev_open or pass_rate < 90:
        return "No-Go", reasons
    if failures or skipped:
        if failures:
            reasons.append(f"{len(failures)} lower-priority failure(s): " + ", ".join(f["tc"] for f in failures))
        if skipped:
            reasons.append(f"{skipped} test(s) skipped")
        return "Go with risks", reasons
    return "Go", ["All executed tests passed; no open defects; no P1/P2 failures."]


def save_summary(run, cfg) -> dict:
    s = build_summary(run, cfg)
    run.write_json("summary.json", s)
    return s


def load_history(runs_dir: Path) -> list[dict]:
    out = []
    for d in sorted(runs_dir.glob("run-*")):
        f = d / "summary.json"
        if f.exists():
            out.append(json.loads(f.read_text(encoding="utf-8")))
    return out


def _e(x):
    return html.escape(str(x))


def _trend(history: list[dict]) -> str:
    if not history:
        return ""
    cells = []
    for h in history:
        pr = h["totals"]["pass_rate"]
        color = {"Go": "#16803c", "No-Go": "#b42318"}.get(h["verdict"], "#b45309")
        height = max(6, int(pr * 0.8))
        cells.append(
            f'<td style="vertical-align:bottom"><div style="width:46px;height:{height}px;background:{color};'
            f'margin:0 auto"></div><div>{pr}%</div><div class="muted">{h["totals"]["total"]} tests</div>'
            f'<div class="muted">{_e(h["verdict"])}</div>'
            f'<div class="muted">{_e(h["label"] or h["run_id"][4:])}</div></td>')
    return f'<table class="bar"><tr>{"".join(cells)}</tr></table>'


def render_report(s: dict, history: list[dict], title="QA Release Readiness Report") -> str:
    vcls = "v-" + s["verdict"].replace(" ", "-")
    t = s["totals"]
    suite_rows = "".join(
        f"<tr><td>{k.upper()}</td><td>{v['total']}</td><td class='pass'>{v['passed']}</td>"
        f"<td class='fail'>{v['failed']}</td><td class='skip'>{v['skipped']}</td><td>{v['duration_s']}s</td></tr>"
        for k, v in s["suites"].items())
    mod_rows = "".join(
        f"<tr><td><code>{_e(m['module'])}</code></td><td>{_e(m['folder'])}</td><td>{m['tests']}</td>"
        f"<td class='pass'>{m['passed']}</td><td class='{'fail' if m['failed'] else ''}'>{m['failed']}</td>"
        f"<td class='muted'>{_e(', '.join(m['tcs']))}</td></tr>" for m in s["modules"])
    fail_html = ""
    if s["failures"]:
        items = "".join(
            f"<div class='card'><b class='fail'>{_e(f['tc'])}</b> {_e(f['title'])} "
            f"<span class='muted'>({f['suite'].upper()}, {f['priority']})</span><br>"
            f"Suspect module: <code>{_e(f['module'])}</code> in folder <code>{_e(_folder(f['module']))}</code>"
            f"<pre>{_e((f.get('error') or '')[-700:])}</pre></div>" for f in s["failures"])
        fail_html = f"<h2>Failing tests and suspect modules</h2>{items}"
    defect_html = ""
    if s["defects"]:
        dr = "".join(f"<tr><td>{_e(d['id'])}</td><td>{_e(d.get('severity',''))}</td><td>{_e(d.get('status',''))}</td>"
                     f"<td>{_e(d.get('classification',''))}</td><td>{_e(d.get('title',''))}</td>"
                     f"<td><code>{_e(d.get('suspect_module',''))}</code></td></tr>" for d in s["defects"])
        by_sev = ", ".join(f"{k}: {v}" for k, v in sorted(Counter(d.get("severity", "?") for d in s["defects"]).items()))
        by_st = ", ".join(f"{k}: {v}" for k, v in sorted(Counter(d.get("status", "?") for d in s["defects"]).items()))
        defect_html = (f"<h2>Defects</h2><div class='muted'>By severity: {_e(by_sev)} &middot; By status: {_e(by_st)}</div>"
                       "<table><tr><th>ID</th><th>Severity</th><th>Status</th>"
                       f"<th>Class</th><th>Title</th><th>Suspect module</th></tr>{dr}</table>")
    reasons = "".join(f"<li>{_e(r)}</li>" for r in s["reasons"])
    hist_rows = "".join(
        f"<tr><td>{_e(h['run_id'])}</td><td>{_e(h['label'])}</td><td>{h['totals']['passed']}/{h['totals']['total']}</td>"
        f"<td>{h['totals']['pass_rate']}%</td><td>{_e(h['verdict'])}</td></tr>" for h in history)
    label = (" &middot; " + _e(s["label"])) if s["label"] else ""
    change_html = ""
    if s.get("change"):
        ch = s["change"]
        nc = "".join(f"<tr><td>{_e(c['id'])}</td><td>{_e(c['layer'])}</td><td>{_e(c['title'])}</td>"
                     f"<td><code>{_e(c['module'])}</code></td>"
                     f"<td class='{'pass' if c['outcome'] == 'passed' else 'fail'}'>{_e(c['outcome'])}</td></tr>"
                     for c in s["new_cases"])
        files = ", ".join(f"<code>{_e(f)}</code>" for f in ch["changed_files"])
        change_html = (f"<h2>Change under test (developer PR)</h2><div class='card'><b>{_e(ch['title'])}</b><br>"
                       f"<span class='muted'>{_e(ch['url'])} &middot; branch {_e(ch['branch'])} &middot; "
                       f"risk: {_e(ch['risk'])}</span><p>{_e(ch['impact'])}</p>Changed files: {files}</div>"
                       "<h2>New test cases added for this change</h2>"
                       "<table><tr><th>ID</th><th>Layer</th><th>Title</th><th>Module</th><th>Result</th></tr>"
                       f"{nc}</table>")
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{_e(title)}</title>
<style>{CSS}</style></head><body><div class="wrap">
<h1>{_e(title)}</h1>
<div class="muted">Run {_e(s['run_id'])}{label} &middot; {_e(s['when'])} &middot; app commit {_e(s['app_git'] or 'n/a')}</div>
<div class="verdict {vcls}">Release verdict: <b>{_e(s['verdict'])}</b><ul>{reasons}</ul></div>
<div class="card"><b>{t['passed']}</b> passed &middot; <b>{t['failed']}</b> failed &middot; <b>{t['skipped']}</b> skipped
 of <b>{t['total']}</b> tests &middot; pass rate <b>{t['pass_rate']}%</b></div>
{change_html}
<h2>Execution summary by suite</h2>
<table><tr><th>Suite</th><th>Total</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Duration</th></tr>{suite_rows}</table>
<h2>Modules covered</h2>
<table><tr><th>Module (source file)</th><th>Folder</th><th>Tests</th><th>Pass</th><th>Fail</th><th>Test cases</th></tr>{mod_rows}</table>
{fail_html}{defect_html}
<h2>Trend across runs</h2>{_trend(history)}
<table style="margin-top:10px"><tr><th>Run</th><th>Label</th><th>Passed</th><th>Pass rate</th><th>Verdict</th></tr>{hist_rows}</table>
<p class="muted">Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} by QA Orchestrator.</p>
</div></body></html>"""


def write_report(run, cfg) -> Path:
    s = save_summary(run, cfg)
    history = load_history(cfg["_root"] / cfg["paths"]["runs_dir"])
    run.path("report.html").write_text(render_report(s, history), encoding="utf-8")
    dash = cfg["_root"] / "dashboard"
    dash.mkdir(exist_ok=True)
    (dash / "index.html").write_text(render_report(s, history, "QA Dashboard - latest run and trend"),
                                     encoding="utf-8")
    return run.path("report.html")
