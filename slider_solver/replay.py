"""匹配录制库并自动拖动。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from slider_solver.auto_drag import drag_slider
from slider_solver.config import load_config
from slider_solver.records import MatchHit, match_record
from slider_solver.screen_match import Region, find_on_screen


@dataclass
class ReplayResult:
    ok: bool
    message: str
    record_id: str = ""
    score: float = 0.0
    distance: int = 0


def _knob_center(match, template_path: str | Path) -> tuple[int, int]:
    data = np.fromfile(str(template_path), dtype=np.uint8)
    tpl = cv2.imdecode(data, cv2.IMREAD_COLOR)
    tw, th = tpl.shape[1], tpl.shape[0]
    return match.screen_x + tw // 2, match.screen_y + th // 2


def replay_hit(hit: MatchHit, cfg: dict | None = None) -> ReplayResult:
    cfg = cfg or load_config()
    rec = hit.record
    region = Region.from_dict(rec.captcha_region)
    tpl = rec.knob_template
    if not Path(tpl).is_file():
        return ReplayResult(False, f"模板丢失: {tpl}", record_id=rec.id, score=hit.score)

    match = find_on_screen(tpl, region, threshold=0.5)
    if not match:
        # 回退：用录制时的起点
        knob_x, knob_y = rec.start_x, rec.start_y
    else:
        knob_x, knob_y = _knob_center(match, tpl)

    distance = rec.drag_distance + int(cfg.get("offset_x") or 0)
    duration = int(rec.duration_ms or cfg.get("drag_duration_ms") or 900)
    drag_slider(knob_x, knob_y, distance, duration_ms=duration)
    return ReplayResult(
        True,
        f"已复现「{rec.name}」距离={distance}px 匹配={hit.score:.2f}",
        record_id=rec.id,
        score=hit.score,
        distance=distance,
    )


def auto_solve_from_library(cfg: dict | None = None) -> ReplayResult:
    cfg = cfg or load_config()
    region = Region.from_dict(cfg.get("captcha_region"))
    if not region:
        return ReplayResult(False, "请先框选验证码区域")

    hit = match_record(region, threshold=float(cfg.get("match_threshold") or 0.88))
    if not hit:
        n = len(__import__("slider_solver.records", fromlist=["list_records"]).list_records())
        return ReplayResult(False, f"未匹配到已保存的验证图（库内 {n} 条）")

    return replay_hit(hit, cfg)
