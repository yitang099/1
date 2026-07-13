"""Resolve built-in data folder next to the executable."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def get_app_dir() -> Path:
  if getattr(sys, "frozen", False):
    return Path(sys.executable).resolve().parent
  return Path(__file__).resolve().parent


def get_data_dir() -> Path:
  return get_app_dir() / "data"


def ensure_data_dir() -> Path:
  data = get_data_dir()
  data.mkdir(parents=True, exist_ok=True)
  readme = data / "使用说明.txt"
  if not readme.exists():
    readme.write_text(
      "把 WeGame 的 data 文件夹内容复制到这里（或整个 data 目录拖进来）。\n"
      "然后打开软件，输入 QQ 号查询封号。\n\n"
      "若扫不到登录态，可在此目录新建 cookies.ini：\n"
      "[account]\n"
      "uin=你的QQ号\n"
      "skey=你的skey\n",
      encoding="utf-8",
    )
  return data


def open_data_folder() -> None:
  path = ensure_data_dir()
  if sys.platform == "win32":
    os.startfile(path)  # type: ignore[attr-defined]
  else:
    import subprocess

    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, str(path)])
