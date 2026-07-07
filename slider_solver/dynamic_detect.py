"""动态滑块缺口识别（ ndarray 版，多算法）。"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from slider_solver.gap_detect import GapResult(piece_rgba: np.ndarray) -> tuple[np.ndarray, np.ndarray | None]:
    if piece_rgba.ndim == 3 and piece_rgba.shape[2] == 4:
        alpha = piece_rgba[:, :, 3]
        piece = piece_rgba[:, :, :3]
        mask = (alpha > 30).astype(np.uint8) * 255
        return piece, mask
    piece = piece_rgba[:, :, :3] if piece_rgba.ndim == 3 else piece_rgba
    return piece, None


def detect_by_template_ndarray(bg: np.ndarray, piece: np.ndarray, mask: np.ndarray | None = None) -> GapResult:
    bg_gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)
    piece_gray = cv2.cvtColor(piece, cv2.COLOR_BGR2GRAY) if piece.ndim == 3 else piece
    if mask is not None:
        res = cv2.matchTemplate(bg_gray, piece_gray, cv2.TM_CCOEFF_NORMED, mask=mask)
    else:
        res = cv2.matchTemplate(bg_gray, piece_gray, cv2.TM_CCOEFF_NORMED)
    _, confidence, _, (x, y) = cv2.minMaxLoc(res)
    return GapResult(x=int(x), y=int(y), confidence=float(confidence), method="template")


def detect_by_sobel(bg: np.ndarray) -> GapResult:
    """缺口边缘竖线检测。"""
    gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    col = np.abs(sx).sum(axis=0)
    w = len(col)
    start = max(8, int(w * 0.12))
    end = max(start + 1, int(w * 0.95))
    region = col[start:end]
    if region.max() <= 0:
        return GapResult(0, 0, 0.0, "sobel")
    x = int(start + np.argmax(region))
    conf = float(region.max() / max(col.max(), 1.0))
    return GapResult(x=x, y=0, confidence=conf, method="sobel")


def detect_by_channel_diff(bg: np.ndarray) -> GapResult:
    """拼图缺口通常颜色与周围不同。"""
    lab = cv2.cvtColor(bg, cv2.COLOR_BGR2LAB)
    l = lab[:, :, 0].astype(np.float32)
    w = l.shape[1]
    start = max(8, int(w * 0.12))
    scores = []
    for x in range(start, w - 4):
        left = l[:, max(0, x - 3) : x].mean() if x > 0 else l.mean()
        right = l[:, x : min(w, x + 3)].mean()
        scores.append(abs(left - right))
    if not scores:
        return GapResult(0, 0, 0.0, "channel")
    idx = int(np.argmax(scores))
    x = start + idx
    conf = float(max(scores) / (np.mean(scores) + 1e-3))
    conf = min(conf / 5.0, 1.0)
    return GapResult(x=x, y=0, confidence=conf, method="channel")


def detect_gap_ndarray(
    bg_bgr: np.ndarray,
    piece_rgba: np.ndarray | None = None,
) -> GapResult:
    candidates: list[GapResult] = []

    if piece_rgba is not None:
        piece, mask = _piece_bgr_and_mask(piece_rgba)
        if piece.shape[0] < bg_bgr.shape[0] and piece.shape[1] < bg_bgr.shape[1]:
            t = detect_by_template_ndarray(bg_bgr, piece, mask)
            candidates.append(t)
            # 排除左侧滑块轨，取右侧最佳匹配
            bg_gray = cv2.cvtColor(bg_bgr, cv2.COLOR_BGR2GRAY)
            piece_gray = cv2.cvtColor(piece, cv2.COLOR_BGR2GRAY)
            if mask is not None:
                res = cv2.matchTemplate(bg_gray, piece_gray, cv2.TM_CCOEFF_NORMED, mask=mask)
            else:
                res = cv2.matchTemplate(bg_gray, piece_gray, cv2.TM_CCOEFF_NORMED)
            w = res.shape[1]
            skip = max(1, int(w * 0.15))
            sub = res[:, skip:]
            _, conf2, _, (x2, y2) = cv2.minMaxLoc(sub)
            candidates.append(GapResult(x=int(x2 + skip), y=int(y2), confidence=float(conf2), method="template_right"))

    candidates.append(detect_by_sobel(bg_bgr))
    candidates.append(detect_by_channel_diff(bg_bgr))

    # 选置信度最高且 x 在合理范围
    valid = [c for c in candidates if c.x > 5]
    if not valid:
        return candidates[0] if candidates else GapResult(0, 0, 0.0, "none")
    return max(valid, key=lambda c: c.confidence)


def draw_result_ndarray(bg: np.ndarray, result: GapResult, piece_width: int = 0) -> np.ndarray:
    img = bg.copy()
    x, h = result.x, img.shape[0]
    cv2.line(img, (x, 0), (x, h - 1), (0, 0, 255), 2)
    if piece_width > 0:
        cv2.rectangle(img, (x, 0), (x + piece_width, h - 1), (0, 255, 0), 2)
    cv2.putText(
        img,
        f"x={x} {result.method} {result.confidence:.2f}",
        (5, 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 0, 255),
        1,
    )
    return img
