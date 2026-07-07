"""Local settings for 8081 test client."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _app_dir()
CONFIG_PATH = APP_DIR / "sms8081_config.json"

DEFAULTS = {
    "sms_base": "http://47.76.163.227:8081",
    "api_secret": "18cdfb81a4e44a3a915528e67d923dba",
    "area_code": "86",
    "proxy": "",
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)
    out = dict(DEFAULTS)
    out.update({k: data[k] for k in DEFAULTS if k in data})
    return out


def save_config(data: dict) -> None:
    out = dict(DEFAULTS)
    out.update({k: data[k] for k in DEFAULTS if k in data})
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
