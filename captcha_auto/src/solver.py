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


def solve_once(cfg, force_type=None):
    region = cfg["region"]
    motion_cfg = cfg.get("motion", {})

    if force_type == "image":
        frame = grab_region(region)
        result, err = solve_image_pick(frame, cfg["api"])
        if err:
            return False, err
    elif force_type == "motion":
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
    else:
        probe = grab_region(region)
        if looks_like_motion(
            probe,
            motion_cfg.get("min_area", 8),
            motion_cfg.get("max_area", 800),
        ):
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
            if not err:
                pass
            else:
                result, err = solve_image_pick(probe, cfg["api"])
                if err:
                    return False, err
        else:
            result, err = solve_image_pick(probe, cfg["api"])
            if err:
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
