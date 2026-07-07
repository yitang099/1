"""两步验证自动过 — 按字选图 + 最慢球。"""
from __future__ import annotations

import json
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "verify_config.json"

DEFAULTS = {
    "step1_region": None,
    "step2_ball_region": None,
    "confirm_template": "",
    "ball_frames": 12,
    "ball_interval_ms": 120,
    "confirm_offset_x": 0,
    "confirm_offset_y": 0,
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
    out = dict(DEFAULTS)
    out.update(data)
    CONFIG_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
