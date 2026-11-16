"""Future provider: Anthropic API (for hosted/CI runs). Needs `pip install anthropic` + ANTHROPIC_API_KEY."""
import os
from pathlib import Path

from .base import LLMProvider
from .claude_code import _agent_prompt


class AnthropicProvider(LLMProvider):
    def __init__(self, conf: dict, root: Path):
        self.model = conf["model"]
        self.root = root

    def run_agent(self, agent: str, task: str, cwd: Path) -> str:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise SystemExit("ANTHROPIC_API_KEY not set (required for llm.provider=anthropic).")
        import anthropic

        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=self.model, max_tokens=8000,
            system=_agent_prompt(self.root, agent),
            messages=[{"role": "user", "content": task}],
        )
        return "".join(b.text for b in msg.content if b.type == "text")
