import argparse
import getpass
import json

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


def cmd_run(cfg, args):
    run = Run.latest(cfg["_root"] / cfg["paths"]["runs_dir"])
    run.require_approved_plan()  # Gate 1 enforced in code
    print("Gate 1 passed. (execution stage: TODO)")


def main():
    p = argparse.ArgumentParser(prog="qa", description="QA Orchestrator")
    p.add_argument("--config")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(fn=cmd_init)
    sub.add_parser("plan").set_defaults(fn=cmd_plan)
    ap = sub.add_parser("approve")
    ap.add_argument("what", choices=["plan"])
    ap.set_defaults(fn=cmd_approve)
    sub.add_parser("run").set_defaults(fn=cmd_run)
    args = p.parse_args()
    args.fn(load_config(args.config), args)


if __name__ == "__main__":
    main()
