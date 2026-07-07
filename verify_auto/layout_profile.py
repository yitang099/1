"""验证小窗相对布局：框选一次，随机位置时自动跟。"""
from __future__ import annotations

from slider_solver.screen_match import Region, grab_region
from verify_auto.ocr_util import find_anchor_line, ocr_lines

STEP1_ANCHORS = ("选择最符合", "描述的图片", "最符合描述")
STEP2_ANCHORS = ("请点击运动", "运动最慢", "最慢的元素")


def compute_anchor_local(prompt_region: Region) -> dict:
    img = grab_region(prompt_region)
    line = find_anchor_line(ocr_lines(img), list(STEP1_ANCHORS) + list(STEP2_ANCHORS))
    if line:
        return {"left": line.left, "top": line.top, "text": line.text}
    return {"left": 0, "top": 0, "text": ""}


def build_layout_profile(cfg: dict) -> dict | None:
    prompt = Region.from_dict(cfg.get("prompt_region"))
    grid = Region.from_dict(cfg.get("grid_region"))
    ball = Region.from_dict(cfg.get("step2_ball_region"))
    if not prompt or not grid or not ball:
        return None

    anchor_local = compute_anchor_local(prompt)
    return {
        "anchor_local": anchor_local,
        "prompt": {"w": prompt.width, "h": prompt.height},
        "grid": {
            "dx": grid.left - prompt.left,
            "dy": grid.top - prompt.top,
            "w": grid.width,
            "h": grid.height,
        },
        "ball": {
            "dx": ball.left - prompt.left,
            "dy": ball.top - prompt.top,
            "w": ball.width,
            "h": ball.height,
        },
    }


def update_layout_profile(cfg: dict) -> bool:
    profile = build_layout_profile(cfg)
    if not profile:
        return False
    cfg["layout_profile"] = profile
    cfg["auto_locate"] = True
    from verify_auto.locate_cache import invalidate_cache

    invalidate_cache()
    return True
