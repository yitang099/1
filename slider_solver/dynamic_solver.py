"""动态滑块：每次截图重新识别缺口（图会变）。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from slider_solver.auto_drag import drag_slider
from slider_solver.config import OUTPUT_DIR, load_config
from slider_solver.dynamic_detect import GapResult, detect_gap_ndarray, draw_result_ndarray
from slider_solver.screen_match import Region, find_template, grab_region


@dataclass
class DynamicResult:
    ok: bool
    message: str
    distance: int = 0
    gap_x: int = 0
    knob_x: int = 0
    confidence: float = 0.0


def _tpl_size(path: str) -> tuple[int, int]:
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return img.shape[1], img.shape[0]


def solve_dynamic(cfg: dict | None = None, *, preview: bool = False) -> DynamicResult:
    cfg = cfg or load_config()
    region = Region.from_dict(cfg.get("captcha_region"))
    if not region:
        return DynamicResult(False, "请先框选验证码区域")

    knob_tpl = (cfg.get("knob_template") or cfg.get("slider_template") or "").strip()
    piece_tpl = (cfg.get("piece_template") or cfg.get("bg_template") or knob_tpl).strip()
    offset = int(cfg.get("offset_x") or 0)

    cap_bgr = grab_region(region)
    OUTPUT_DIR.mkdir(exist_ok=True)
    cv2.imencode(".png", cap_bgr)[1].tofile(str(OUTPUT_DIR / "last_dynamic.png"))

    knob_left = int(cfg.get("knob_margin_x") or 12)
    knob_cx = region.left + knob_left + 20
    knob_cy = region.top + region.height // 2

    if knob_tpl and Path(knob_tpl).is_file():
        m = find_template(cap_bgr, knob_tpl, threshold=0.45)
        if m:
            tw, th = _tpl_size(knob_tpl)
            knob_left = m.x
            knob_cx = region.left + m.x + tw // 2
            knob_cy = region.top + m.y + th // 2

    piece_bgr = None
    if piece_tpl and Path(piece_tpl).is_file():
        piece_bgr = cv2.imdecode(np.fromfile(piece_tpl, dtype=np.uint8), cv2.IMREAD_UNCHANGED)

    gap: GapResult = detect_gap_ndarray(cap_bgr, piece_bgr)
    if gap.confidence < 0.15:
        return DynamicResult(
            False,
            f"缺口识别弱(conf={gap.confidence:.2f})，请框选【拼图块】模板后点「预览识别」",
            gap_x=gap.x,
            confidence=gap.confidence,
        )

    distance = int(gap.x - knob_left + offset)
    if distance < 10:
        distance = int(gap.x + offset)

    if preview:
        pw = _tpl_size(piece_tpl)[0] if piece_tpl and Path(piece_tpl).is_file() else 0
        prev = draw_result_ndarray(cap_bgr, gap, piece_width=pw)
        cv2.line(prev, (knob_left, 0), (knob_left, prev.shape[0] - 1), (255, 0, 0), 2)
        cv2.imencode(".png", prev)[1].tofile(str(OUTPUT_DIR / "dynamic_preview.png"))
        return DynamicResult(
            True,
            f"预览: 缺口x={gap.x} 滑块左={knob_left} 距离={distance} ({gap.method})",
            distance=distance,
            gap_x=gap.x,
            knob_x=knob_left,
            confidence=gap.confidence,
        )

    if distance <= 0:
        return DynamicResult(False, f"距离无效 {distance}px，调 X微调")

    duration = int(cfg.get("drag_duration_ms") or 900)
    drag_slider(knob_cx, knob_cy, distance, duration_ms=duration)
    return DynamicResult(
        True,
        f"动态拖动 {distance}px（缺口={gap.x} {gap.method} conf={gap.confidence:.2f}）",
        distance=distance,
        gap_x=gap.x,
        knob_x=knob_left,
        confidence=gap.confidence,
    )
