"""Run state: every run lives in runs/<run-id>/ and gates are enforced here."""
import hashlib
import json
from datetime import datetime
from pathlib import Path


def new_run_id() -> str:
    return datetime.now().strftime("run-%Y%m%d-%H%M%S")


class Run:
    def __init__(self, runs_dir: Path, run_id: str):
        self.id = run_id
        self.dir = runs_dir / run_id
        self.dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def latest(cls, runs_dir: Path) -> "Run":
        runs = sorted(p.name for p in runs_dir.glob("run-*") if p.is_dir())
        if not runs:
            raise SystemExit("No runs yet. Start with: qa init")
        return cls(runs_dir, runs[-1])

    def path(self, name: str) -> Path:
        return self.dir / name

    def write_json(self, name: str, data) -> Path:
        p = self.path(name)
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return p

    def read_json(self, name: str):
        return json.loads(self.path(name).read_text(encoding="utf-8"))

    # ---- Gate 1: the plan must be approved, and unchanged since approval ----
    @staticmethod
    def _hash(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    def approve_plan(self, approver: str) -> None:
        plan = self.path("test_cases.json")
        if not plan.exists():
            raise SystemExit("No test_cases.json to approve. Run: qa plan")
        self.write_json("approved.json", {
            "approver": approver,
            "at": datetime.now().isoformat(timespec="seconds"),
            "sha256": self._hash(plan),
        })

    def require_approved_plan(self) -> None:
        a, plan = self.path("approved.json"), self.path("test_cases.json")
        if not a.exists():
            raise SystemExit("Gate 1: test plan not approved. Review it, then: qa approve plan")
        if json.loads(a.read_text())["sha256"] != self._hash(plan):
            raise SystemExit("Gate 1: test_cases.json changed after approval. Re-run: qa approve plan")
