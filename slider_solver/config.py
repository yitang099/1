"""桌面滑块自动拖动 — 配置读写。"""
from __future__ import annotations

import json
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "slider_config.json"
TEMPLATES_DIR = APP_DIR / "templates"
OUTPUT_DIR = APP_DIR / "output"
RECORDS_DIR = APP_DIR / "records"

DEFAULTS = {
  "captcha_region": None,
  "slider_template": "",
  "bg_template": "",
  "manual_distance": 0,
  "offset_x": 0,
  "drag_duration_ms": 900,
  "match_threshold": 0.88,
  "cooldown_sec": 3,
  "watch_interval_ms": 600,
  "hotkey": "f8",
  "hotkey_record": "f9",
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
    OUTPUT_DIR.mkdir(exist_ok=True)
    RECORDS_DIR.mkdir(exist_ok=True)
    out = dict(DEFAULTS)
    out.update(data)
    CONFIG_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
