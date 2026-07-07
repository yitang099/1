"""自动推断验证码弹窗区域（免框选）。"""
from __future__ import annotations

import cv2
import numpy as np

from slider_solver.screen_match import Region, grab_region
from verify_auto.ocr_util import OcrLine
from verify_auto.region_resolve import CaptchaRegions
from verify_auto.window_locate import find_anchor_on_screen, union_search_region


def _find_light_dialog(bgr: np.ndarray, anchor: OcrLine) -> Region | None:
    h, w = bgr.shape[:2]
    pad = 280
    x1 = max(0, anchor.left - pad)
    y1 = max(0, anchor.top - pad)
    x2 = min(w, anchor.right + pad)
    y2 = min(h, anchor.bottom + pad + 380)
    crop = bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    for lo, hi in ((190, 255), (170, 255), (200, 255)):
        mask = cv2.inRange(gray, lo, hi)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        ax, ay = anchor.left - x1, anchor.top - y1
        best: Region | None = None
        best_score = -1.0
        for c in cnts:
            x, y, bw, bh = cv2.boundingRect(c)
            if bw < 160 or bh < 180 or bw > 780 or bh > 780:
                continue
            if not (x - 20 <= ax <= x + bw + 20 and y - 20 <= ay <= y + bh + 20):
                continue
            score = bw * bh - abs(bw - 360) * 3 - abs(bh - 430) * 3
            if score > best_score:
                best_score = score
                best = Region(x1 + x, y1 + y, bw, bh)
        if best:
            return best
    return None


def _layout_from_dialog(dialog: Region, anchor: OcrLine) -> CaptchaRegions:
    prompt_h = max(40, min(64, anchor.height + 22))
    prompt_top = max(dialog.top, anchor.top - 10)
    prompt = Region(dialog.left + 6, prompt_top, dialog.width - 12, prompt_h)

    content_top = prompt.top + prompt.height + 6
    content_h = max(140, dialog.top + dialog.height - content_top - 52)
    grid = Region(dialog.left + 6, content_top, dialog.width - 12, content_h)
    ball = grid
    step2_prompt = Region(prompt.left, prompt.top, prompt.width, prompt.height)
    search = union_search_region(prompt, step2_prompt, grid, ball) or dialog
    return CaptchaRegions(
        step1_prompt=prompt,
        step2_prompt=step2_prompt,
        grid=grid,
        ball=ball,
        search=search or dialog,
        auto=True,
        anchor_text=anchor.text,
    )


def _layout_from_anchor(anchor: OcrLine) -> CaptchaRegions:
    dialog = Region(max(0, anchor.left - 18), max(0, anchor.top - 16), 380, 440)
    return _layout_from_dialog(dialog, anchor)


def auto_detect_regions(*, step_hint: int = 0) -> CaptchaRegions | None:
    anchor = find_anchor_on_screen(step_hint=step_hint)
    if not anchor:
        return None
    screen = grab_region(None)
    dialog = _find_light_dialog(screen, anchor)
    if dialog:
        return _layout_from_dialog(dialog, anchor)
    return _layout_from_anchor(anchor)


def auto_detect_regions_robust(*, step_hint: int = 0) -> CaptchaRegions | None:
    """多策略找窗：指定 hint → 0 → 1 → 2。"""
    hints = [step_hint] if step_hint else []
    for h in hints + [0, 1, 2]:
        if h in hints[:-1]:
            continue
        hit = auto_detect_regions(step_hint=h)
        if hit:
            return hit
    return None
