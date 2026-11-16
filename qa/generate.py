"""Stage 2: ask an agent to write test code for the approved cases. Python writes the files."""
import json
import re
from pathlib import Path

from .llm import LLMProvider

FILE_RE = re.compile(r"=== FILE: (.+?) ===\n(.*?)\n=== END ===", re.S)
API_SOURCES = ["backend/app/api/routes/items.py", "backend/app/api/routes/users.py",
               "backend/app/api/routes/login.py", "backend/app/models.py", "backend/app/api/deps.py"]


def _write_blocks(text: str, root: Path, allowed_prefix: str) -> list[str]:
    written = []
    for path, body in FILE_RE.findall(text):
        path = path.strip().replace("\\", "/")
        if not path.startswith(allowed_prefix) or ".." in path:
            raise RuntimeError(f"Agent tried to write outside {allowed_prefix}: {path}")
        body = re.sub(r"^```\w*\n|\n```$", "", body.strip())
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body + "\n", encoding="utf-8")
        written.append(path)
    if not written:
        raise RuntimeError("Agent returned no file blocks. Raw output start: " + text[:300])
    return written


def generate_api(llm: LLMProvider, cfg: dict, cases: list[dict]) -> list[str]:
    repo = cfg["_target_repo"]
    api_cases = [c for c in cases if c["layer"] == "API"]
    sources = "\n\n".join(f"### {p}\n{(repo / p).read_text(encoding='utf-8')}" for p in API_SOURCES)
    task = (f"Write tests for these {len(api_cases)} approved API cases.\n\n"
            f"## CASES\n{json.dumps(api_cases, indent=1)}\n\n## APP SOURCE\n{sources}")
    text = llm.run_agent("api-tester", task, cfg["_root"])
    written = _write_blocks(text, cfg["_root"], "generated/api/")
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
