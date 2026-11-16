"""Run state: every run lives in runs/<run-id>/ and gates are enforced here."""
import hashlib
import json
import shutil
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

    def has_results(self) -> bool:
        return self.path("results_api.json").exists() or self.path("results_ui.json").exists()

    def clone_for_execution(self) -> "Run":
        """New run folder reusing this run's approved plan (same hash, so Gate 1 still holds)."""
        new = Run(self.dir.parent, new_run_id())
        for f in ("context.json", "test_cases.json", "approved.json"):
            shutil.copy(self.path(f), new.path(f))
        return new

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

    def reapprove_amended(self, approver: str, note: str, tcs: list) -> None:
        """Plan amended through a Gate 2 'update the test' decision: re-hash, keep an audit trail."""
        a = json.loads(self.path("approved.json").read_text(encoding="utf-8"))
        a.setdefault("amendments", []).append(
            {"by": approver, "at": datetime.now().isoformat(timespec="seconds"), "note": note, "tcs": tcs})
        a["sha256"] = self._hash(self.path("test_cases.json"))
        self.write_json("approved.json", a)

    def require_approved_plan(self) -> None:
        a, plan = self.path("approved.json"), self.path("test_cases.json")
        if not a.exists():
            raise SystemExit("Gate 1: test plan not approved. Review it, then: qa approve plan")
        if json.loads(a.read_text())["sha256"] != self._hash(plan):
            raise SystemExit("Gate 1: test_cases.json changed after approval. Re-run: qa approve plan")
