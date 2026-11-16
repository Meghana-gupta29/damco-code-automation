"""Stage 2: ask an agent to write test code for the approved cases. Python writes the files."""
import json
import re
from pathlib import Path

from .llm import LLMProvider

FILE_RE = re.compile(r"=== FILE: (.+?) ===\n(.*?)\n=== END ===", re.S)
API_SOURCES = ["backend/app/api/routes/items.py", "backend/app/api/routes/users.py",
               "backend/app/api/routes/login.py", "backend/app/models.py", "backend/app/api/deps.py"]


def existing_tc_ids(root: Path) -> set[str]:
    """Case ids that already have a generated test."""
    ids = set()
    for f in (root / "generated").rglob("*"):
        if f.suffix in (".py", ".ts") and f.name != "conftest.py":
            ids |= set(re.findall(r'(?:mark\.tc\("|test\(\s*["`\'])(TC-\d+)', f.read_text(encoding="utf-8")))
    return ids


def _write_blocks(text: str, root: Path, allowed_prefix: str, exact: str | None = None) -> list[str]:
    written = []
    for path, body in FILE_RE.findall(text):
        path = path.strip().replace("\\", "/")
        if not path.startswith(allowed_prefix) or ".." in path:
            raise RuntimeError(f"Agent tried to write outside {allowed_prefix}: {path}")
        if exact and (path != exact or (root / path).exists()):
            raise RuntimeError(f"Incremental generation must create only the new file {exact}; agent wrote {path}")
        body = re.sub(r"^```\w*\n|\n```$", "", body.strip())
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body + "\n", encoding="utf-8")
        written.append(path)
    if not written:
        raise RuntimeError("Agent returned no file blocks. Raw output start: " + text[:300])
    return written


def _incremental_note(new_file: str | None) -> str:
    if not new_file:
        return ""
    return (f"INCREMENTAL: existing tests are already written and must not be touched. Write ONLY these new cases, "
            f"in exactly ONE new file at the path `{new_file}`. Reuse existing helpers/fixtures.\n\n")


def generate_api(llm: LLMProvider, cfg: dict, cases: list[dict], only_ids: set | None = None,
                 new_file: str | None = None) -> list[str]:
    repo = cfg["_target_repo"]
    api_cases = [c for c in cases if c["layer"] == "API" and (only_ids is None or c["id"] in only_ids)]
    sources = "\n\n".join(f"### {p}\n{(repo / p).read_text(encoding='utf-8')}" for p in API_SOURCES)
    conftest = (cfg["_root"] / "generated/api/conftest.py").read_text(encoding="utf-8")
    task = (f"{_incremental_note(new_file)}Write tests for these {len(api_cases)} approved API cases.\n\n"
            f"## CASES\n{json.dumps(api_cases, indent=1)}\n\n"
            f"## EXISTING FIXTURES (generated/api/conftest.py; use exactly these signatures)\n{conftest}\n\n"
            f"## APP SOURCE\n{sources}")
    text = llm.run_agent("api-tester", task, cfg["_root"])
    written = _write_blocks(text, cfg["_root"], "generated/api/", new_file)
    ids = {c["id"] for c in api_cases}
    used = set()
    for f in written:
        src = (cfg["_root"] / f).read_text(encoding="utf-8")
        used |= set(re.findall(r'mark\.tc\("(TC-\d+)"\)', src))
    unknown, missing = used - ids, ids - used
    if unknown:
        raise RuntimeError(f"Agent wrote tests for ids not in the approved plan: {sorted(unknown)}")
    if missing:
        raise RuntimeError(f"Approved cases without a test: {sorted(missing)}")
    return written


UI_SOURCE_GLOBS = ["frontend/src/routes/login.tsx", "frontend/src/routes/signup.tsx",
                   "frontend/src/routes/_layout/*.tsx", "frontend/src/components/Items/*.tsx",
                   "frontend/src/components/UserSettings/*.tsx", "frontend/src/components/Admin/*.tsx",
                   "frontend/src/components/Common/UserMenu.tsx", "frontend/src/components/Common/Appearance.tsx"]
UI_REFERENCE = ["frontend/tests/items.spec.ts", "frontend/tests/user-settings.spec.ts",
                "frontend/tests/admin.spec.ts", "frontend/tests/utils/user.ts"]


def generate_ui(llm: LLMProvider, cfg: dict, cases: list[dict], only_ids: set | None = None,
                new_file: str | None = None) -> list[str]:
    repo = cfg["_target_repo"]
    ui_cases = [c for c in cases if c["layer"] == "UI" and (only_ids is None or c["id"] in only_ids)]
    files = []
    for g in UI_SOURCE_GLOBS:
        files += sorted(repo.glob(g))
    src = "\n\n".join(f"### {p.relative_to(repo).as_posix()}\n{p.read_text(encoding='utf-8')}" for p in files)
    ref = "\n\n".join(f"### {p}\n{(repo / p).read_text(encoding='utf-8')}" for p in UI_REFERENCE
                      if (repo / p).exists())
    helpers = (cfg["_root"] / "generated/ui/helpers.ts").read_text(encoding="utf-8")
    task = (f"{_incremental_note(new_file)}Write Playwright tests for these {len(ui_cases)} approved UI cases.\n\n"
            f"## CASES\n{json.dumps(ui_cases, indent=1)}\n\n"
            f"## EXISTING HELPERS (generated/ui/helpers.ts; use exactly these signatures, e.g. "
            f"createUserViaApi takes an options object and returns the id)\n{helpers}\n\n"
            f"## FRONTEND SOURCE\n{src}\n\n"
            f"## REFERENCE: template's own Playwright tests (selector idioms only)\n{ref}")
    text = llm.run_agent("ui-tester", task, cfg["_root"])
    written = _write_blocks(text, cfg["_root"], "generated/ui/", new_file)
    ids = {c["id"] for c in ui_cases}
    used = set()
    for f in written:
        used |= set(re.findall(r'test\(\s*["\x60\'](TC-\d+)', (cfg["_root"] / f).read_text(encoding="utf-8")))
    if used - ids:
        raise RuntimeError(f"Agent wrote UI tests for ids not in the approved plan: {sorted(used - ids)}")
    if ids - used:
        raise RuntimeError(f"Approved UI cases without a test: {sorted(ids - used)}")
    return written
