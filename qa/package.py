"""qa package: copy real run evidence into submission/evidence (nothing hand-written)."""
import json
import shutil
from collections import Counter

KEEP = ["report.html", "summary.json", "results_api.json", "results_ui.json", "decisions.json",
        "plan_delta.json", "pr_context.json", "approved.json"]


def package(cfg: dict) -> None:
    root = cfg["_root"]
    runs_dir = root / cfg["paths"]["runs_dir"]
    out = root / "submission" / "evidence"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    lines = ["# Evidence index", "", "Copied by `qa package` from real runs. Open `report.html` in each folder.", "",
             "| Run | Label | Tests passed | Verdict | Defects (severity: status) |", "|---|---|---|---|---|"]
    n = 0
    for d in sorted(runs_dir.glob("run-*")):
        f = d / "summary.json"
        if not f.exists():
            continue
        s = json.loads(f.read_text(encoding="utf-8"))
        dest = out / f"{d.name}_{s['label'] or 'run'}"
        dest.mkdir()
        for name in KEEP:
            if (d / name).exists():
                shutil.copy(d / name, dest / name)
        if (d / "defects").is_dir():
            shutil.copytree(d / "defects", dest / "defects")
            shutil.copy(d / "defects.json", dest / "defects.json")
        shots = list((d / "ui-artifacts").rglob("*.png")) if (d / "ui-artifacts").exists() else []
        if shots:
            (dest / "failure-screenshots").mkdir()
            for i, p in enumerate(shots, 1):
                shutil.copy(p, dest / "failure-screenshots" / f"{i}_{p.parent.name[:60]}.png")
        dc = ", ".join(f"{x['id']} {x['severity']}: {x['status']}" for x in s["defects"]) or "none"
        t = s["totals"]
        lines.append(f"| {d.name} | {s['label']} | {t['passed']}/{t['total']} | {s['verdict']} | {dc} |")
        n += 1
    if (root / "dashboard" / "index.html").exists():
        shutil.copy(root / "dashboard" / "index.html", out / "dashboard.html")
    (out / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Packaged {n} run(s) into {out}")
    print("Reminder: `qa reset-demo` deletes run folders; package first, then commit submission/evidence.")
