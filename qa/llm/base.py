"""Agents talk to an LLMProvider, never to a vendor directly.

Switching from local Claude Code to the Anthropic API is a config change
(llm.provider), not a code change.
"""
import json
import re
from abc import ABC, abstractmethod
from pathlib import Path


class LLMProvider(ABC):
    @abstractmethod
    def run_agent(self, agent: str, task: str, cwd: Path) -> str:
        """Run agent `agent` (prompt in .claude/agents/<agent>.md) on `task`; return text."""

    def run_agent_json(self, agent: str, task: str, cwd: Path, schema: dict | None = None):
        """Run an agent expected to return JSON; validate and retry once."""
        import jsonschema

        last_err = None
        for attempt in range(2):
            prompt = task if attempt == 0 else f"{task}\n\nYour previous output was invalid ({last_err}). Return ONLY valid JSON."
            text = self.run_agent(agent, prompt, cwd)
            try:
                data = extract_json(text)
                if schema:
                    jsonschema.validate(data, schema)
                return data
            except Exception as e:  # noqa: BLE001
                last_err = str(e)[:300]
        raise RuntimeError(f"Agent '{agent}' returned invalid output twice: {last_err}")


def extract_json(text: str):
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    return json.loads(m.group(1) if m else text)


def get_provider(cfg: dict) -> LLMProvider:
    name = cfg["llm"]["provider"]
    if name == "claude_code":
        from .claude_code import ClaudeCodeProvider
        return ClaudeCodeProvider(cfg["llm"]["claude_code"], cfg["_root"])
    if name == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(cfg["llm"]["anthropic"], cfg["_root"])
    raise SystemExit(f"Unknown llm.provider: {name}")
