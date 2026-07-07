"""鼠标拖动执行。"""
from __future__ import annotations

import random
import time

import pyautogui

from slider_solver.track import generate_track

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


def drag_slider(
    start_x: int,
    start_y: int,
    distance: int,
    *,
    duration_ms: int = 900,
) -> list[int]:
    """从滑块中心按住拖到目标距离。"""
    track = generate_track(distance, duration_ms=duration_ms)
    pyautogui.moveTo(start_x, start_y, duration=random.uniform(0.08, 0.15))
    time.sleep(random.uniform(0.05, 0.12))
    pyautogui.mouseDown()
    time.sleep(random.uniform(0.03, 0.08))

    cx, cy = start_x, start_y
    n = max(len(track.offsets), 1)
    step_sleep = (duration_ms / 1000.0) / n
    for dx in track.offsets:
        cx += dx
        pyautogui.moveTo(cx, cy, duration=max(0.01, step_sleep * random.uniform(0.8, 1.2)))
    pyautogui.mouseUp()
    return track.offsets
