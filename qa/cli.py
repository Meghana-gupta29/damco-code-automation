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
    from .generate import existing_tc_ids, generate_api, generate_ui
    run = Run.latest(cfg["_root"] / cfg["paths"]["runs_dir"])
    run.require_approved_plan()  # Gate 1 enforced in code
    cases = run.read_json("test_cases.json")
    llm = get_provider(cfg)
    only, tag = None, None
    if args.new_only:  # tests only for approved cases that have no test yet (PR-driven flow)
        have = existing_tc_ids(cfg["_root"])
        only = {c["id"] for c in cases if c["id"] not in have}
        tag = run.read_json("pr_context.json")["tag"] if run.path("pr_context.json").exists() else "new"
        print(f"New cases without tests: {', '.join(sorted(only)) or 'none'}")
    for suite, fn, path in (("api", generate_api, f"generated/api/test_{tag}.py"),
                            ("ui", generate_ui, f"generated/ui/{tag}.spec.ts")):
        if args.suite not in (suite, "all"):
            continue
        layer = suite.upper()
        if only is not None and not any(c["id"] in only and c["layer"] == layer for c in cases):
            print(f"No new {layer} cases; skipping.")
            continue
        files = fn(llm, cfg, cases, only, path if only is not None else None)
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
    prev = None
    if run.has_results():
        prev, run = run, run.clone_for_execution()  # every execution is its own run (needed for the trend)
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
    from .cleanup import cleanup_test_users
    try:
        matched, deleted = cleanup_test_users(cfg)
        print(f"Cleanup: removed {deleted} leftover test user(s).")
    except Exception as e:  # noqa: BLE001  (cleanup problems must never fail a run)
        print(f"Cleanup skipped: {e}")
    if prev is not None:
        from .fixflow import carry_defects
        carry_defects(prev, run)  # defects whose tests now pass are closed; others stay open
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
    g.add_argument("suite", choices=["api", "ui", "all"])
    g.add_argument("--new-only", action="store_true", help="only write tests for approved cases lacking one")
    g.set_defaults(fn=cmd_generate)
    rp = sub.add_parser("run")
    rp.add_argument("--suite", choices=["api", "ui"])
    rp.add_argument("--label", default="")
    sub.add_parser("report").set_defaults(fn=cmd_report)
    sub.add_parser("email").set_defaults(fn=cmd_email)
    rp.set_defaults(fn=cmd_run)

    from . import appctl
    sub.add_parser("triage").set_defaults(fn=lambda cfg, a: __import__("qa.triage", fromlist=["x"]).triage_and_report(
        cfg, Run.latest(cfg["_root"] / cfg["paths"]["runs_dir"])))
    dp = sub.add_parser("decide", help="Gate 2: choose fix code or update test per defect")
    dp.add_argument("--defect")
    dp.add_argument("--choice", choices=["code", "test", "skip"])
    dp.set_defaults(fn=lambda cfg, a: __import__("qa.fixflow", fromlist=["x"]).decide(
        cfg, Run.latest(cfg["_root"] / cfg["paths"]["runs_dir"]), a.defect, a.choice))
    fp = sub.add_parser("fix", help="apply the decisions (shows a diff and asks to confirm)")
    fp.add_argument("--yes", action="store_true", help="skip the confirmation prompts")
    fp.set_defaults(fn=lambda cfg, a: __import__("qa.fixflow", fromlist=["x"]).apply_fixes(
        cfg, Run.latest(cfg["_root"] / cfg["paths"]["runs_dir"]), a.yes))
    sp = sub.add_parser("sabotage")
    sp.add_argument("action", choices=["apply", "revert"])
    sp.set_defaults(fn=lambda cfg, a: appctl.sabotage_apply(cfg) if a.action == "apply" else appctl.sabotage_revert(cfg))
    ap2 = sub.add_parser("app")
    ap2.add_argument("action", choices=["deploy", "status"])
    ap2.set_defaults(fn=lambda cfg, a: appctl.deploy(cfg) if a.action == "deploy" else appctl.status(cfg))
    cl = sub.add_parser("cleanup", help="delete leftover test users (same cleanup that runs after every run)")
    cl.add_argument("--dry-run", action="store_true", help="only count what would be deleted")

    def _cleanup(cfg, a):
        from .cleanup import cleanup_test_users
        m, d = cleanup_test_users(cfg, dry_run=a.dry_run)
        print(f"{'Would delete' if a.dry_run else 'Deleted'} {m if a.dry_run else d} test user(s).")
    cl.set_defaults(fn=_cleanup)
    sub.add_parser("package", help="copy run evidence into submission/evidence").set_defaults(
        fn=lambda cfg, a: __import__("qa.package", fromlist=["x"]).package(cfg))
    fa = sub.add_parser("feature", help="play the developer: feature branch (+ real PR on the fork)")
    fa.add_argument("action", choices=["apply"])
    fa.add_argument("--pr", action="store_true", help="push the branch and open a pull request")
    fa.set_defaults(fn=lambda cfg, a: __import__("qa.prsync", fromlist=["x"]).feature_apply(cfg, a.pr))
    ps = sub.add_parser("pr-sync", help="QA agent reads a PR, assesses impact, proposes new test cases")
    ps.add_argument("--pr", type=int)
    ps.add_argument("--branch")
    ps.add_argument("--max-new", type=int, default=1, help="max new cases per layer")
    ps.set_defaults(fn=lambda cfg, a: __import__("qa.prsync", fromlist=["x"]).pr_sync(cfg, a.pr, a.branch, a.max_new))
    rd = sub.add_parser("reset-demo", help="clear runs/mailbox, restore tests, app back to base branch")
    rd.add_argument("--deploy", action="store_true")
    rd.set_defaults(fn=lambda cfg, a: __import__("qa.demo", fromlist=["x"]).reset_demo(cfg, a.deploy))
    args = p.parse_args()
    args.fn(load_config(args.config), args)


if __name__ == "__main__":
    main()
