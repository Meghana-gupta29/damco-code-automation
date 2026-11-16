from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: str | Path | None = None) -> dict:
    load_dotenv(ROOT / ".env")
    cfg_path = Path(path) if path else ROOT / "qa.config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["_root"] = ROOT
    cfg["_target_repo"] = (ROOT / cfg["target"]["repo_path"]).resolve()
    return cfg
