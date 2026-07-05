import time

import pyautogui

from .image_solver import solve_image_pick
from .motion_solver import looks_like_motion, solve_motion
from .screen import grab_frames, grab_region, region_to_screen


pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


def _click_screen(sx, sy, delay_ms=300):
    pyautogui.moveTo(sx, sy, duration=0.08)
    pyautogui.click()
    time.sleep(delay_ms / 1000.0)


def _click_confirm(cfg):
    region = cfg["region"]
    btn = cfg.get("confirm_button", {})
    ox = btn.get("offset_x", 0)
    oy = btn.get("offset_y", 0)
    if ox == 0 and oy == 0:
        sx = region["left"] + region["width"] - 45
        sy = region["top"] + 28
    else:
        sx = region["left"] + region["width"] - ox
        sy = region["top"] + oy
    _click_screen(sx, sy, cfg.get("click_delay_ms", 300))


def _pick_type(probe, cfg, detect_reason=None):
    motion_cfg = cfg.get("motion", {})
    min_a = motion_cfg.get("min_area", 8)
    max_a = motion_cfg.get("max_area", 800)
    is_motion = looks_like_motion(probe, min_a, max_a)

    if detect_reason:
        if "motion" in detect_reason and "image" not in detect_reason:
            return "motion"
        if "image" in detect_reason and "motion" not in detect_reason:
            return "image"
    if is_motion:
        return "motion"
    return "image"


def solve_once(cfg, force_type=None, detect_reason=None):
    region = cfg["region"]
    motion_cfg = cfg.get("motion", {})

    if force_type is None:
        force_type = _pick_type(grab_region(region), cfg, detect_reason)

    if force_type == "image":
        frame = grab_region(region)
        result, err = solve_image_pick(frame, cfg["api"])
        if err:
            return False, err
    else:
        frames = grab_frames(
            region,
            motion_cfg.get("frames", 18),
            motion_cfg.get("interval_ms", 150),
        )
        result, err = solve_motion(
            frames,
            motion_cfg.get("min_area", 8),
            motion_cfg.get("max_area", 800),
        )
        if err:
            return False, err

    sx, sy = region_to_screen(region, result["x"], result["y"])
    _click_screen(sx, sy, cfg.get("click_delay_ms", 300))
    _click_confirm(cfg)
    return True, result.get("detail", "ok")
