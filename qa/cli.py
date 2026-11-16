import argparse
import getpass
import json
import subprocess
from datetime import datetime

from .config import load_config
from .discover import discover
from .llm import get_provider
from .state import Run, new_run_id


def cmd_init(cfg, args):
    run = Run(cfg["_root"] / cfg["paths"]["runs_dir"], new_run_id())
    run.write_json("context.json", discover(cfg["_target_repo"]))
    print(f"Created {run.id}; context.json has {len(run.read_json('context.json')['endpoints'])} endpoints.")


def cmd_plan(cfg, args):
    run = Run.latest(cfg["_root"] / cfg["paths"]["runs_dir"])
    ctx = run.read_json("context.json")
    llm = get_provider(cfg)
    cases = llm.run_agent_json(
        "test-designer",
        "Design test cases for the flow sign-up -> login -> items CRUD -> user settings.\n"
        f"Context:\n{json.dumps(ctx, indent=2)}",
        cwd=cfg["_root"],
    )
    run.write_json("test_cases.json", cases)
    print(f"Plan written to {run.path('test_cases.json')}\nReview/edit it, then: qa approve plan")


def cmd_approve(cfg, args):
    run = Run.latest(cfg["_root"] / cfg["paths"]["runs_dir"])
    run.approve_plan(getpass.getuser())
    print("Plan approved (hash recorded).")


def cmd_generate(cfg, args):
    from .generate import generate_api, generate_ui
    run = Run.latest(cfg["_root"] / cfg["paths"]["runs_dir"])
    run.require_approved_plan()  # Gate 1 enforced in code
    cases = run.read_json("test_cases.json")
    if args.suite == "api":
        files = generate_api(get_provider(cfg), cfg, cases)
    else:
        files = generate_ui(get_provider(cfg), cfg, cases)
    print("Wrote:")
    for f in files:
        print("  " + f)


def _app_git(repo) -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo, capture_output=True,
                             text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "backend", "frontend"], cwd=repo,
                               capture_output=True, text=True).stdout.strip()
        return sha + ("+local-changes" if dirty else "")
    except Exception:  # noqa: BLE001
        return ""


def cmd_report(cfg, args):
    from .report import write_report
    run = Run.latest(cfg["_root"] / cfg["paths"]["runs_dir"])
    print("Report:", write_report(run, cfg))


def cmd_email(cfg, args):
    from .emailer import send_report
    run = Run.latest(cfg["_root"] / cfg["paths"]["runs_dir"])
    inbox = send_report(cfg, run)
    print(f"Report emailed. Open the inbox: {inbox}")


def cmd_run(cfg, args):
    from .report import write_report
    from .runner import run_api, run_ui
    run = Run.latest(cfg["_root"] / cfg["paths"]["runs_dir"])
    run.require_approved_plan()  # Gate 1 enforced in code
    if run.has_results():
        run = run.clone_for_execution()  # every execution is its own run (needed for the trend)
    run.write_json("meta.json", {"label": args.label, "started": datetime.now().isoformat(timespec="seconds"),
                                 "app_git": _app_git(cfg["_target_repo"])})
    print(f"Run {run.id} {args.label}")
    suites = {"api": run_api, "ui": run_ui}
    for name in ([args.suite] if args.suite else ["api", "ui"]):
        rows = suites[name](cfg, run)["rows"]
        n = lambda o: sum(r["outcome"] == o for r in rows)  # noqa: E731
        print(f"{name.upper()}: {len(rows)} tests | passed {n('passed')} | failed {n('failed')} | skipped {n('skipped')}")
        for r in rows:
            if r["outcome"] == "failed":
                print(f"  FAIL {r['tc']} {r['test']}")
    report = write_report(run, cfg)
    print(f"Verdict: {run.read_json('summary.json')['verdict']}  report: {report}")


def main():
    p = argparse.ArgumentParser(prog="qa", description="QA Orchestrator")
    p.add_argument("--config")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(fn=cmd_init)
    sub.add_parser("plan").set_defaults(fn=cmd_plan)
    ap = sub.add_parser("approve")
    ap.add_argument("what", choices=["plan"])
    ap.set_defaults(fn=cmd_approve)
    g = sub.add_parser("generate")
    g.add_argument("suite", choices=["api", "ui"])
    g.set_defaults(fn=cmd_generate)
    rp = sub.add_parser("run")
    rp.add_argument("--suite", choices=["api", "ui"])
    rp.add_argument("--label", default="")
    sub.add_parser("report").set_defaults(fn=cmd_report)
    sub.add_parser("email").set_defaults(fn=cmd_email)
    rp.set_defaults(fn=cmd_run)
    args = p.parse_args()
    args.fn(load_config(args.config), args)


if __name__ == "__main__":
    main()
