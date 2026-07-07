"""自动推断验证码弹窗区域（免框选）。"""
from __future__ import annotations

import cv2
import numpy as np

from slider_solver.screen_match import Region, grab_region
from verify_auto.ocr_util import OcrLine
from verify_auto.region_resolve import CaptchaRegions
from verify_auto.window_locate import find_anchor_on_screen, union_search_region


def _find_light_dialog(bgr: np.ndarray, anchor: OcrLine) -> Region | None:
    """在锚点附近找浅色弹窗矩形。"""
    h, w = bgr.shape[:2]
    pad = 220
    x1 = max(0, anchor.left - pad)
    y1 = max(0, anchor.top - pad)
    x2 = min(w, anchor.right + pad)
    y2 = min(h, anchor.bottom + pad + 320)
    crop = bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    mask = cv2.inRange(gray, 200, 255)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ax, ay = anchor.left - x1, anchor.top - y1
    best: Region | None = None
    best_score = -1.0
    for c in cnts:
        x, y, bw, bh = cv2.boundingRect(c)
        if bw < 180 or bh < 200 or bw > 700 or bh > 700:
            continue
        if not (x <= ax <= x + bw and y <= ay <= y + bh):
            continue
        area = bw * bh
        score = area - abs(bw - 340) * 2 - abs(bh - 400) * 2
        if score > best_score:
            best_score = score
            best = Region(x1 + x, y1 + y, bw, bh)
    return best


def _layout_from_dialog(dialog: Region, anchor: OcrLine) -> CaptchaRegions:
    prompt_h = max(36, min(56, anchor.height + 18))
    prompt_top = max(dialog.top, anchor.top - 8)
    prompt = Region(dialog.left + 8, prompt_top, dialog.width - 16, prompt_h)

    content_top = prompt.top + prompt.height + 4
    content_h = max(120, dialog.top + dialog.height - content_top - 48)
    grid = Region(dialog.left + 8, content_top, dialog.width - 16, content_h)
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
    """锚点 + 典型弹窗尺寸兜底。"""
    dialog_w, dialog_h = 360, 420
    left = max(0, anchor.left - 16)
    top = max(0, anchor.top - 14)
    dialog = Region(left, top, dialog_w, dialog_h)
    return _layout_from_dialog(dialog, anchor)


def auto_detect_regions(*, step_hint: int = 0) -> CaptchaRegions | None:
    """全屏 OCR 找验证窗并自动推算各区域。"""
    anchor = find_anchor_on_screen(step_hint=step_hint)
    if not anchor:
        return None

    screen = grab_region(None)
    dialog = _find_light_dialog(screen, anchor)
    if dialog:
        return _layout_from_dialog(dialog, anchor)
    return _layout_from_anchor(anchor)
