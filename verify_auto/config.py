"""配置。"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _app_dir()
CONFIG_PATH = APP_DIR / "verify_config.json"
TEMPLATES_DIR = APP_DIR / "templates"
DEBUG_DIR = APP_DIR / "debug"
LIBRARY_DIR = APP_DIR / "library"

DEFAULTS = {
    "prompt_region": None,
    "step1_prompt_region": None,
    "step2_prompt_region": None,
    "grid_region": None,
    "step2_ball_region": None,
    "confirm_template": "",
    "grid_rows": 2,
    "grid_cols": 3,
    "ball_frames": 15,
    "ball_interval_ms": 100,
    "step2_wait_sec": 2.5,
    "keyword_override": "",
    "use_library": True,
    "step1_min_score": 0.72,
    "auto_locate": True,
    "background_click": True,
    "enable_prefetch": False,
    "layout_profile": None,
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
    if not out.get("step1_prompt_region") and out.get("prompt_region"):
        out["step1_prompt_region"] = out["prompt_region"]
    if not out.get("step2_prompt_region"):
        out["step2_prompt_region"] = out.get("step1_prompt_region") or out.get("prompt_region")
    if out.get("step1_prompt_region"):
        out["prompt_region"] = out["step1_prompt_region"]
    return out


def save_config(data: dict) -> None:
    TEMPLATES_DIR.mkdir(exist_ok=True)
    DEBUG_DIR.mkdir(exist_ok=True)
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    out = dict(DEFAULTS)
    out.update(data)
    CONFIG_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
