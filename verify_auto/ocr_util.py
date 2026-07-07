"""OCR 工具：返回文字与边框。"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class OcrLine:
    text: str
    score: float
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height


def _box_to_rect(box) -> tuple[int, int, int, int]:
    xs = [int(p[0]) for p in box]
    ys = [int(p[1]) for p in box]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    return left, top, max(1, right - left), max(1, bottom - top)


def ocr_lines(bgr: np.ndarray) -> list[OcrLine]:
    try:
        from rapidocr_onnxruntime import RapidOCR

        engine = RapidOCR()
        result, _ = engine(bgr)
        if not result:
            return []
        lines: list[OcrLine] = []
        for item in result:
            box, text, score = item[0], str(item[1]), float(item[2])
            left, top, w, h = _box_to_rect(box)
            lines.append(OcrLine(text=text, score=score, left=left, top=top, width=w, height=h))
        return lines
    except ImportError:
        pass
    try:
        import easyocr

        reader = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)
        raw = reader.readtext(bgr)
        lines: list[OcrLine] = []
        for box, text, score in raw:
            left, top, w, h = _box_to_rect(box)
            lines.append(OcrLine(text=text, score=float(score), left=left, top=top, width=w, height=h))
        return lines
    except ImportError:
        return []


def ocr_text(bgr: np.ndarray) -> str:
    return " ".join(line.text for line in ocr_lines(bgr))


def find_anchor_line(lines: list[OcrLine], anchors: list[str]) -> OcrLine | None:
    best: OcrLine | None = None
    best_score = -1.0
    for line in lines:
        for anchor in anchors:
            if anchor not in line.text:
                continue
            s = line.score + len(anchor) * 0.01
            if s > best_score:
                best_score = s
                best = line
    return best
