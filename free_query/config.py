"""Local config persistence."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _app_dir()
CONFIG_PATH = APP_DIR / "config.json"

DEFAULTS = {
    "username": "",
    "password": "",
    "main_base": "http://43.154.128.116:9110",
    "sms_base": "http://47.76.163.227:8081",
    "proxy": "",
    "area_code": "86",
    "auto_topup": True,
    "topup_amount": 9999.0,
    "min_balance": 10.0,
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in data.items() if k in DEFAULTS})
    return merged


def save_config(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = dict(DEFAULTS)
    out.update({k: data[k] for k in DEFAULTS if k in data})
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
