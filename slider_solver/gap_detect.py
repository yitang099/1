"""滑块缺口位置识别（OpenCV）。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class GapResult:
    x: int
    y: int
    confidence: float
    method: str


def _read_bgr(path: str | Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"无法读取图片: {path}")
    return img


def _read_rgba(path: str | Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"无法读取图片: {path}")
    return img


def detect_by_template(bg_path: str | Path, piece_path: str | Path) -> GapResult:
    """背景图 + 滑块小图 → 模板匹配。"""
    bg = _read_bgr(bg_path)
    piece_rgba = _read_rgba(piece_path)
    if piece_rgba.ndim == 3 and piece_rgba.shape[2] == 4:
        alpha = piece_rgba[:, :, 3]
        piece = piece_rgba[:, :, :3]
        mask = (alpha > 30).astype(np.uint8) * 255
    else:
        piece = piece_rgba[:, :, :3] if piece_rgba.ndim == 3 else piece_rgba
        mask = None

    bg_gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)
    piece_gray = cv2.cvtColor(piece, cv2.COLOR_BGR2GRAY)

    if mask is not None:
        res = cv2.matchTemplate(bg_gray, piece_gray, cv2.TM_CCOEFF_NORMED, mask=mask)
    else:
        res = cv2.matchTemplate(bg_gray, piece_gray, cv2.TM_CCOEFF_NORMED)

    _, confidence, _, (x, y) = cv2.minMaxLoc(res)
    return GapResult(x=int(x), y=int(y), confidence=float(confidence), method="template")


def detect_by_edge(bg_path: str | Path) -> GapResult:
    """仅背景图 → 边缘缺口检测（无滑块小图时用）。"""
    bg = _read_bgr(bg_path)
    gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(gray, 80, 200)

    col_sum = edges.sum(axis=0).astype(np.float32)
    if col_sum.max() <= 0:
        return GapResult(x=0, y=0, confidence=0.0, method="edge")

    # 忽略最左侧滑轨区域
    start = max(10, int(len(col_sum) * 0.1))
    region = col_sum[start:]
    x = int(start + int(np.argmax(region)))
    conf = float(region.max() / max(col_sum.max(), 1.0))
    return GapResult(x=x, y=0, confidence=conf, method="edge")


def detect_gap(
    bg_path: str | Path,
    piece_path: str | Path | None = None,
) -> GapResult:
    if piece_path and Path(piece_path).is_file():
        r = detect_by_template(bg_path, piece_path)
        if r.confidence >= 0.35:
            return r
    return detect_by_edge(bg_path)


def draw_result(bg_path: str | Path, result: GapResult, piece_width: int = 0) -> np.ndarray:
    img = _read_bgr(bg_path).copy()
    x = result.x
    h = img.shape[0]
    cv2.line(img, (x, 0), (x, h - 1), (0, 0, 255), 2)
    if piece_width > 0:
        cv2.rectangle(img, (x, 0), (x + piece_width, h - 1), (0, 255, 0), 2)
    label = f"x={x} conf={result.confidence:.2f} ({result.method})"
    cv2.putText(img, label, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    return img
