"""全屏 OCR 定位验证小窗（随机位置）。"""
from __future__ import annotations

import cv2
import numpy as np

from slider_solver.screen_match import Region, grab_region
from verify_auto.layout_profile import STEP1_ANCHORS, STEP2_ANCHORS
from verify_auto.ocr_util import OcrLine, find_anchor_line, ocr_lines

MAX_OCR_WIDTH = 1920


def _scale_for_ocr(bgr: np.ndarray) -> tuple[np.ndarray, float]:
    h, w = bgr.shape[:2]
    if w <= MAX_OCR_WIDTH:
        return bgr, 1.0
    scale = MAX_OCR_WIDTH / w
    small = cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return small, scale


def find_anchor_on_screen(step_hint: int = 0) -> OcrLine | None:
    """在全屏里找验证提示行。step_hint: 1 / 2 / 0(自动)。"""
    img, scale = _scale_for_ocr(grab_region(None))
    lines = ocr_lines(img)
    if scale != 1.0:
        scaled: list[OcrLine] = []
        inv = 1.0 / scale
        for line in lines:
            scaled.append(
                OcrLine(
                    text=line.text,
                    score=line.score,
                    left=int(line.left * inv),
                    top=int(line.top * inv),
                    width=int(line.width * inv),
                    height=int(line.height * inv),
                )
            )
        lines = scaled

    if step_hint == 2:
        order = (list(STEP2_ANCHORS), list(STEP1_ANCHORS))
    else:
        order = (list(STEP1_ANCHORS), list(STEP2_ANCHORS))

    for anchors in order:
        hit = find_anchor_line(lines, anchors)
        if hit:
            return hit
    return None


def regions_from_profile(profile: dict, anchor: OcrLine) -> tuple[Region, Region, Region]:
    al = profile.get("anchor_local") or {}
    prompt_left = anchor.left - int(al.get("left") or 0)
    prompt_top = anchor.top - int(al.get("top") or 0)

    p = profile["prompt"]
    g = profile["grid"]
    b = profile["ball"]

    prompt = Region(prompt_left, prompt_top, int(p["w"]), int(p["h"]))
    grid = Region(
        prompt_left + int(g["dx"]),
        prompt_top + int(g["dy"]),
        int(g["w"]),
        int(g["h"]),
    )
    ball = Region(
        prompt_left + int(b["dx"]),
        prompt_top + int(b["dy"]),
        int(b["w"]),
        int(b["h"]),
    )
    return prompt, grid, ball


def union_search_region(*regions: Region | None, pad: int = 36) -> Region | None:
    valid = [r for r in regions if r]
    if not valid:
        return None
    left = min(r.left for r in valid) - pad
    top = min(r.top for r in valid) - pad
    right = max(r.left + r.width for r in valid) + pad
    bottom = max(r.top + r.height for r in valid) + pad
    return Region(max(0, left), max(0, top), max(1, right - left), max(1, bottom - top))
