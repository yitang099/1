"""Local config for QQ bind hook client."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_dir() -> Path:
    """PyInstaller 打包资源目录（datas）。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


APP_VERSION = "1.2.4"

APP_DIR = app_dir()
CONFIG_PATH = APP_DIR / "qq_bind_config.json"
RESULTS_DIR_NAME = "查Q结果"

DEFAULTS = {
    "adb_path": "",
    "frida_server_path": "",
    "qq_package": "com.tencent.mobileqq",
    "auto_start_frida": True,
    "auto_hook_on_connect": False,
    "try_msf_process": True,
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)
    out = dict(DEFAULTS)
    out.update({k: data[k] for k in DEFAULTS if k in data})
    return out


def save_config(data: dict) -> None:
    out = dict(DEFAULTS)
    out.update({k: data[k] for k in DEFAULTS if k in data})
    CONFIG_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


def results_dir() -> Path:
    p = APP_DIR / RESULTS_DIR_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p
