"""验证小窗相对布局：框选一次，随机位置时自动跟。"""
from __future__ import annotations

from slider_solver.screen_match import Region, grab_region
from verify_auto.ocr_util import find_anchor_line, ocr_lines

STEP1_ANCHORS = ("选择最符合", "描述的图片", "最符合描述")
STEP2_ANCHORS = ("请点击运动", "运动最慢", "最慢的元素")


def _prompt_regions(cfg: dict) -> tuple[Region | None, Region | None]:
    s1 = Region.from_dict(cfg.get("step1_prompt_region") or cfg.get("prompt_region"))
    s2 = Region.from_dict(cfg.get("step2_prompt_region") or s1)
    return s1, s2


def compute_anchor_local(prompt_region: Region, anchors: tuple[str, ...]) -> dict:
    img = grab_region(prompt_region)
    line = find_anchor_line(ocr_lines(img), list(anchors))
    if line:
        return {"left": line.left, "top": line.top, "text": line.text}
    return {"left": 0, "top": 0, "text": ""}


def build_layout_profile(cfg: dict) -> dict | None:
    s1, s2 = _prompt_regions(cfg)
    grid = Region.from_dict(cfg.get("grid_region"))
    ball = Region.from_dict(cfg.get("step2_ball_region"))
    if not s1 or not s2 or not grid or not ball:
        return None

    return {
        "prompt_offset": {"dx": s2.left - s1.left, "dy": s2.top - s1.top},
        "step1": {
            "anchor_local": compute_anchor_local(s1, STEP1_ANCHORS),
            "prompt": {"w": s1.width, "h": s1.height},
            "grid": {
                "dx": grid.left - s1.left,
                "dy": grid.top - s1.top,
                "w": grid.width,
                "h": grid.height,
            },
        },
        "step2": {
            "anchor_local": compute_anchor_local(s2, STEP2_ANCHORS),
            "prompt": {"w": s2.width, "h": s2.height},
            "ball": {
                "dx": ball.left - s2.left,
                "dy": ball.top - s2.top,
                "w": ball.width,
                "h": ball.height,
            },
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
