"""全屏 OCR 定位验证小窗（随机位置）。"""
from __future__ import annotations

import cv2
import numpy as np

from slider_solver.screen_match import Region, grab_region
from verify_auto.layout_profile import STEP1_ANCHORS, STEP2_ANCHORS
from verify_auto.locate_cache import SEARCH_PAD, cached_window_region
from verify_auto.ocr_util import OcrLine, find_anchor_line, ocr_lines

MAX_OCR_WIDTH = 1600


def _scale_for_ocr(bgr: np.ndarray) -> tuple[np.ndarray, float]:
    h, w = bgr.shape[:2]
    if w <= MAX_OCR_WIDTH:
        return bgr, 1.0
    scale = MAX_OCR_WIDTH / w
    small = cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return small, scale


def _lines_to_screen(lines: list[OcrLine], offset_x: int, offset_y: int, scale: float) -> list[OcrLine]:
    if scale == 1.0 and offset_x == 0 and offset_y == 0:
        return lines
    inv = 1.0 / scale if scale != 1.0 else 1.0
    out: list[OcrLine] = []
    for line in lines:
        out.append(
            OcrLine(
                text=line.text,
                score=line.score,
                left=int(line.left * inv) + offset_x,
                top=int(line.top * inv) + offset_y,
                width=int(line.width * inv),
                height=int(line.height * inv),
            )
        )
    return out


def _pick_anchor(lines: list[OcrLine], step_hint: int) -> OcrLine | None:
    if step_hint == 2:
        return find_anchor_line(lines, list(STEP2_ANCHORS))
    if step_hint == 1:
        return find_anchor_line(lines, list(STEP1_ANCHORS))
    hit = find_anchor_line(lines, list(STEP2_ANCHORS))
    if hit:
        return hit
    return find_anchor_line(lines, list(STEP1_ANCHORS))


def _ocr_region(region: Region, step_hint: int) -> OcrLine | None:
    img, scale = _scale_for_ocr(grab_region(region))
    lines = _lines_to_screen(ocr_lines(img), region.left, region.top, scale)
    return _pick_anchor(lines, step_hint)


def find_anchor_on_screen(step_hint: int = 0) -> OcrLine | None:
    """先搜上次小窗附近（快），没有再全屏搜。"""
    window = cached_window_region()
    if window:
        near = Region(
            max(0, window.left - SEARCH_PAD),
            max(0, window.top - SEARCH_PAD),
            window.width + SEARCH_PAD * 2,
            window.height + SEARCH_PAD * 2,
        )
        hit = _ocr_region(near, step_hint)
        if hit:
            return hit

    img, scale = _scale_for_ocr(grab_region(None))
    lines = _lines_to_screen(ocr_lines(img), 0, 0, scale)
    return _pick_anchor(lines, step_hint)


def _prompt_from_anchor(profile: dict, anchor: OcrLine, step_key: str) -> Region:
    block = profile[step_key]
    al = block.get("anchor_local") or {}
    p = block["prompt"]
    left = anchor.left - int(al.get("left") or 0)
    top = anchor.top - int(al.get("top") or 0)
    return Region(left, top, int(p["w"]), int(p["h"]))


def regions_from_profile(
    profile: dict,
    anchor: OcrLine,
    *,
    step_hint: int = 0,
) -> tuple[Region, Region, Region, Region]:
    """返回 (step1_prompt, step2_prompt, grid, ball) 屏幕坐标。"""
    off = profile.get("prompt_offset") or {"dx": 0, "dy": 0}
    odx, ody = int(off.get("dx") or 0), int(off.get("dy") or 0)

    if step_hint == 2:
        step2_prompt = _prompt_from_anchor(profile, anchor, "step2")
        step1_prompt = Region(
            step2_prompt.left - odx,
            step2_prompt.top - ody,
            int(profile["step1"]["prompt"]["w"]),
            int(profile["step1"]["prompt"]["h"]),
        )
    else:
        step1_prompt = _prompt_from_anchor(profile, anchor, "step1")
        step2_prompt = Region(
            step1_prompt.left + odx,
            step1_prompt.top + ody,
            int(profile["step2"]["prompt"]["w"]),
            int(profile["step2"]["prompt"]["h"]),
        )

    g = profile["step1"]["grid"]
    grid = Region(
        step1_prompt.left + int(g["dx"]),
        step1_prompt.top + int(g["dy"]),
        int(g["w"]),
        int(g["h"]),
    )
    b = profile["step2"]["ball"]
    # 第2步动球通常出现在第1步网格的位置，优先按网格对齐
    dxg = int(b.get("dx_grid", 0))
    dyg = int(b.get("dy_grid", 0))
    ball = Region(
        grid.left + dxg,
        grid.top + dyg,
        int(b["w"]),
        int(b["h"]),
    )
    return step1_prompt, step2_prompt, grid, ball


def union_search_region(*regions: Region | None, pad: int = 36) -> Region | None:
    valid = [r for r in regions if r]
    if not valid:
        return None
    left = min(r.left for r in valid) - pad
    top = min(r.top for r in valid) - pad
    right = max(r.left + r.width for r in valid) + pad
    bottom = max(r.top + r.height for r in valid) + pad
    return Region(max(0, left), max(0, top), max(1, right - left), max(1, bottom - top))
