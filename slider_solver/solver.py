"""一次完整自动过滑块流程。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2

from slider_solver.config import OUTPUT_DIR, load_config
from slider_solver.gap_detect import detect_gap
from slider_solver.screen_match import Region, find_on_screen, grab_region, save_region_image


@dataclass
class SolveResult:
    ok: bool
    message: str
    distance: int = 0
    knob_x: int = 0
    knob_y: int = 0


def _knob_center(match, template_path: str | Path) -> tuple[int, int]:
    import numpy as np

    data = np.fromfile(str(template_path), dtype=np.uint8)
    tpl = cv2.imdecode(data, cv2.IMREAD_COLOR)
    tw, th = tpl.shape[1], tpl.shape[0]
    return match.screen_x + tw // 2, match.screen_y + th // 2


def solve_once(cfg: dict | None = None) -> SolveResult:
    cfg = cfg or load_config()
    region = Region.from_dict(cfg.get("captcha_region"))
    slider_tpl = (cfg.get("slider_template") or "").strip()
    bg_tpl = (cfg.get("bg_template") or "").strip()
    manual = int(cfg.get("manual_distance") or 0)
    offset = int(cfg.get("offset_x") or 0)

    if not slider_tpl or not Path(slider_tpl).is_file():
        return SolveResult(False, "请先截取并保存【滑块按钮】模板")

    match = find_on_screen(slider_tpl, region)
    if not match:
        return SolveResult(False, "屏幕上未找到滑块按钮，请把验证码调出来后再试")

    knob_x, knob_y = _knob_center(match, slider_tpl)
    distance = manual

    if distance <= 0:
        if not region:
            return SolveResult(
                False,
                "未设置拖动距离：请框选验证码区域并保存背景，或填写固定距离(px)",
            )
        cap_path = OUTPUT_DIR / "last_captcha.png"
        save_region_image(region, cap_path)
        piece = bg_tpl if bg_tpl and Path(bg_tpl).is_file() else None
        try:
            gap = detect_gap(cap_path, piece)
            distance = gap.x + offset
        except Exception as exc:
            return SolveResult(False, f"缺口识别失败: {exc}")

    if distance <= 0:
        return SolveResult(False, "拖动距离为 0，请检查识别结果或手动填写距离")

    from slider_solver.auto_drag import drag_slider

    duration = int(cfg.get("drag_duration_ms") or 900)
    drag_slider(knob_x, knob_y, distance, duration_ms=duration)
    return SolveResult(
        True,
        f"已拖动 {distance}px，起点 ({knob_x},{knob_y})",
        distance=distance,
        knob_x=knob_x,
        knob_y=knob_y,
    )
