"""生成本地测试用滑块图。"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def create_demo_pair(out_dir: str | Path, gap_x: int = 180) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    w, h = 320, 160
    bg = np.ones((h, w, 3), dtype=np.uint8) * 230
    for i in range(0, w, 20):
        cv2.line(bg, (i, 0), (i, h), (210, 215, 220), 1)
    for j in range(0, h, 20):
        cv2.line(bg, (0, j), (w, j), (210, 215, 220), 1)

    piece_w, piece_h = 48, 48
    y0 = (h - piece_h) // 2
    piece = bg[y0 : y0 + piece_h, gap_x : gap_x + piece_w].copy()
    cv2.rectangle(piece, (0, 0), (piece_w - 1, piece_h - 1), (80, 120, 200), 2)

    # 背景挖洞
    cv2.rectangle(bg, (gap_x, y0), (gap_x + piece_w, y0 + piece_h), (180, 180, 185), -1)
    cv2.rectangle(bg, (gap_x, y0), (gap_x + piece_w, y0 + piece_h), (100, 100, 110), 2)

    bg_path = out / "demo_bg.png"
    piece_path = out / "demo_piece.png"
    cv2.imencode(".png", bg)[1].tofile(str(bg_path))
    cv2.imencode(".png", piece)[1].tofile(str(piece_path))
    return bg_path, piece_path
