"""Runs an agent through the user's local Claude Code CLI (`claude -p`). No API key."""
import os
import re
import shutil
import subprocess
from pathlib import Path

from .base import LLMProvider


def _agent_prompt(root: Path, agent: str) -> str:
    f = root / ".claude" / "agents" / f"{agent}.md"
    if not f.exists():
        raise SystemExit(f"Agent definition missing: {f}")
    text = f.read_text(encoding="utf-8")
    return re.sub(r"\A---.*?---\s*", "", text, flags=re.S)  # strip frontmatter


class ClaudeCodeProvider(LLMProvider):
    def __init__(self, conf: dict, root: Path):
        self.cmd = conf.get("command", "claude")
        self.timeout = conf.get("timeout_s", 600)
        self.root = root

    def run_agent(self, agent: str, task: str, cwd: Path) -> str:
        exe = shutil.which(self.cmd)
        if not exe:
            raise SystemExit(
                f"'{self.cmd}' not found on PATH. Install Claude Code, or paste the prompt for "
                f"agent '{agent}' into Claude Code manually and save its output as the stage artifact."
            )
        prompt = f"{_agent_prompt(self.root, agent)}\n\n# TASK\n{task}"
        # Isolate the child: drop vars inherited from a parent Claude session, no tools,
        # no persisted session. Agents return text/JSON; Python writes files (deterministic).
        env = {k: v for k, v in os.environ.items()
               if not (k.startswith("CLAUDE") or k == "ANTHROPIC_BASE_URL")}
        res = subprocess.run(
            [exe, "-p", "--output-format", "text", "--no-session-persistence",
             "--disallowedTools", "Bash,Edit,Write,Read,Glob,Grep,WebFetch,WebSearch,Task"],
            input=prompt, cwd=cwd, env=env, capture_output=True, text=True,
            timeout=self.timeout, encoding="utf-8",
        )
        if res.returncode != 0:
            raise RuntimeError(f"claude exited {res.returncode}: {res.stderr[:500]}")
        return res.stdout
