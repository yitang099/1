"""配置。"""
from __future__ import annotations

import json
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "verify_config.json"
TEMPLATES_DIR = APP_DIR / "templates"
DEBUG_DIR = APP_DIR / "debug"

DEFAULTS = {
    "prompt_region": None,
    "grid_region": None,
    "step2_ball_region": None,
    "confirm_template": "",
    "grid_rows": 2,
    "grid_cols": 3,
    "ball_frames": 15,
    "ball_interval_ms": 100,
    "step2_wait_sec": 2.5,
    "keyword_override": "",
    "debug_dir": str(DEBUG_DIR),
}


def load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return dict(DEFAULTS)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)
    out = dict(DEFAULTS)
    out.update(data)
    return out


def save_config(data: dict) -> None:
    TEMPLATES_DIR.mkdir(exist_ok=True)
    DEBUG_DIR.mkdir(exist_ok=True)
    out = dict(DEFAULTS)
    out.update(data)
    CONFIG_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
