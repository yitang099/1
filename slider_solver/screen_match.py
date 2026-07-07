"""屏幕截图与模板定位。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import mss
import numpy as np


@dataclass
class Region:
    left: int
    top: int
    width: int
    height: int

    def as_dict(self) -> dict:
        return {"left": self.left, "top": self.top, "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, d: dict | None) -> Region | None:
        if not d:
            return None
        return cls(int(d["left"]), int(d["top"]), int(d["width"]), int(d["height"]))


@dataclass
class MatchResult:
    x: int
    y: int
    confidence: float
    screen_x: int
    screen_y: int


def grab_region(region: Region | None = None) -> np.ndarray:
    with mss.mss() as sct:
        if region:
            mon = region.as_dict()
        else:
            mon = sct.monitors[1]
        shot = sct.grab(mon)
        img = np.array(shot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def save_region_image(region: Region, path: str | Path) -> Path:
    img = grab_region(region)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    cv2.imencode(".png", img)[1].tofile(str(p))
    return p


def _read(path: str | Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"无法读取: {path}")
    return img


def find_template(
    haystack_bgr: np.ndarray,
    template_path: str | Path,
    *,
    threshold: float = 0.55,
) -> MatchResult | None:
    tpl = _read(template_path)
    th, tw = tpl.shape[:2]
    if haystack_bgr.shape[0] < th or haystack_bgr.shape[1] < tw:
        return None
    res = cv2.matchTemplate(haystack_bgr, tpl, cv2.TM_CCOEFF_NORMED)
    _, conf, _, (x, y) = cv2.minMaxLoc(res)
    if conf < threshold:
        return None
    return MatchResult(x=x, y=y, confidence=float(conf), screen_x=x, screen_y=y)


def find_on_screen(
    template_path: str | Path,
    region: Region | None = None,
    *,
    threshold: float = 0.55,
) -> MatchResult | None:
    img = grab_region(region)
    m = find_template(img, template_path, threshold=threshold)
    if not m:
        return None
    if region:
        m.screen_x += region.left
        m.screen_y += region.top
    return m
