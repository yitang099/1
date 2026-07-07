"""OCR 工具：返回文字与边框。"""
from __future__ import annotations

import threading
from dataclasses import dataclass

import cv2
import numpy as np

_engine = None
_engine_lock = threading.Lock()


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


def _get_rapidocr():
    global _engine
    if _engine is not None:
        return _engine
    with _engine_lock:
        if _engine is None:
            from rapidocr_onnxruntime import RapidOCR

            _engine = RapidOCR()
        return _engine


def warmup_ocr() -> None:
    """后台预加载 OCR 模型，避免首次点击卡顿。"""
    try:
        tiny = np.zeros((32, 128, 3), dtype=np.uint8)
        ocr_lines(tiny)
    except Exception:
        pass


def preprocess_for_ocr(bgr: np.ndarray) -> np.ndarray:
    """放大过小截图并增强对比，提高中文提示识别率。"""
    if bgr is None or bgr.size == 0:
        return bgr
    img = bgr.copy()
    h, w = img.shape[:2]
    min_w = 360
    if w < min_w:
        scale = min_w / max(w, 1)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def ocr_lines(bgr: np.ndarray, *, enhance: bool = True) -> list[OcrLine]:
    src = preprocess_for_ocr(bgr) if enhance else bgr
    try:
        engine = _get_rapidocr()
        result, _ = engine(src)
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
    except Exception:
        pass
    try:
        import easyocr

        reader = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)
        raw = reader.readtext(src)
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
