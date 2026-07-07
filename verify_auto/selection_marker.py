"""检测点击后的选中标记：第1步蓝色勾、第2步蓝色数字圈。"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from slider_solver.screen_match import Region, grab_region
from verify_auto.step1_pick import split_grid


@dataclass
class MarkerHit:
    score: float
    cx: int
    cy: int
    radius: float


def _blue_mask(bgr: np.ndarray) -> np.ndarray:
    """蓝色选中徽章（圆底 + 白勾/白字）。"""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (90, 70, 70), (135, 255, 255))
    b, g, r = cv2.split(bgr)
    bgr_blue = cv2.bitwise_and(b, cv2.bitwise_and(cv2.compare(b, g, cv2.CMP_GT), cv2.compare(b, r, cv2.CMP_GT)))
    mask = cv2.bitwise_or(mask, cv2.inRange(bgr_blue, 120, 255))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    return mask


def _white_mask(bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (0, 0, 185), (180, 60, 255))


def _find_badges(
    bgr: np.ndarray,
    *,
    min_r: int = 8,
    max_r: int = 28,
    min_area: int = 80,
    max_area: int = 2200,
) -> list[MarkerHit]:
    mask = _blue_mask(bgr)
    white = _white_mask(bgr)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hits: list[MarkerHit] = []
    for c in cnts:
        area = cv2.contourArea(c)
        if area < min_area or area > max_area:
            continue
        (fx, fy), fr = cv2.minEnclosingCircle(c)
        r = float(fr)
        if r < min_r or r > max_r:
            continue
        peri = cv2.arcLength(c, True)
        if peri <= 0:
            continue
        circularity = 4 * np.pi * area / (peri * peri)
        if circularity < 0.45:
            continue
        cx, cy = int(fx), int(fy)
        ri = max(4, int(r * 0.55))
        x1, y1 = max(0, cx - ri), max(0, cy - ri)
        x2, y2 = min(bgr.shape[1], cx + ri), min(bgr.shape[0], cy + ri)
        inner = white[y1:y2, x1:x2]
        white_ratio = float(inner.sum()) / max(inner.size, 1) / 255.0
        score = circularity * 0.55 + min(1.0, area / 600.0) * 0.25 + white_ratio * 0.35
        hits.append(MarkerHit(score=score, cx=cx, cy=cy, radius=r))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits


def _cell_corner_roi(cell: np.ndarray, corner: str = "tr") -> np.ndarray:
    h, w = cell.shape[:2]
    cw, ch = max(24, w // 3), max(24, h // 3)
    if corner == "tr":
        return cell[0:ch, w - cw : w]
    if corner == "tl":
        return cell[0:ch, 0:cw]
    if corner == "br":
        return cell[h - ch : h, w - cw : w]
    return cell[h - ch : h, 0:cw]


def detect_step1_selected_cell(
    grid_bgr: np.ndarray,
    *,
    rows: int = 2,
    cols: int = 3,
) -> tuple[int, float] | None:
    """返回被选中的格子序号 (0-based) 与置信度；无勾则 None。"""
    cells = split_grid(grid_bgr, rows, cols)
    best_i = -1
    best_score = 0.0
    for i, cell in enumerate(cells):
        roi = _cell_corner_roi(cell, "tr")
        badges = _find_badges(roi, min_r=6, max_r=22)
        if not badges:
            badges = _find_badges(cell, min_r=6, max_r=24)
        if not badges:
            continue
        s = badges[0].score
        if s > best_score:
            best_score = s
            best_i = i
    if best_i < 0 or best_score < 0.32:
        return None
    return best_i, best_score


def detect_step1_selected_from_region(
    grid_region: Region,
    *,
    rows: int = 2,
    cols: int = 3,
) -> tuple[int, float] | None:
    return detect_step1_selected_cell(grab_region(grid_region), rows=rows, cols=cols)


def detect_step2_selected_ball(ball_bgr: np.ndarray) -> tuple[int, int, float] | None:
    """返回球区域内选中标记中心 (局部 x,y) 与置信度。"""
    hits = _find_badges(ball_bgr, min_r=8, max_r=30, min_area=70, max_area=2600)
    if not hits or hits[0].score < 0.4:
        return None
    h = hits[0]
    return h.cx, h.cy, h.score


def detect_step2_selected_from_region(ball_region: Region) -> tuple[int, int, float] | None:
    return detect_step2_selected_ball(grab_region(ball_region))


def wait_for_step1_marker(
    grid_region: Region,
    *,
    rows: int = 2,
    cols: int = 3,
    timeout_sec: float = 30.0,
    poll_sec: float = 0.5,
) -> tuple[int, float] | None:
    import time

    deadline = time.time() + timeout_sec
    last_hint = 0.0
    while time.time() < deadline:
        hit = detect_step1_selected_from_region(grid_region, rows=rows, cols=cols)
        if hit:
            return hit
        now = time.time()
        if now - last_hint > 5.0:
            last_hint = now
        time.sleep(poll_sec)
    return None


def wait_for_step2_marker(
    ball_region: Region,
    *,
    timeout_sec: float = 45.0,
    poll_sec: float = 0.5,
) -> tuple[int, int, float] | None:
    import time

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        hit = detect_step2_selected_from_region(ball_region)
        if hit:
            return hit
        time.sleep(poll_sec)
    return None
