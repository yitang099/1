"""确定按钮点击（可在后台线程调用）。"""
from __future__ import annotations

import cv2
import numpy as np

from slider_solver.screen_match import Region, find_on_screen
from verify_auto.click_util import click_screen


def click_confirm_button(cfg: dict, search: Region | None = None) -> bool:
    tpl = cfg.get("confirm_template") or ""
    if not tpl:
        return False
    m = find_on_screen(tpl, search, threshold=0.55)
    if not m:
        return False
    img = cv2.imdecode(np.fromfile(str(tpl), dtype=np.uint8), cv2.IMREAD_COLOR)
    cx = m.screen_x + img.shape[1] // 2
    cy = m.screen_y + img.shape[0] // 2
    bg = bool(cfg.get("background_click", True))
    return click_screen(cx, cy, background=bg).ok
