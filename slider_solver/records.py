"""录制库：保存手动过的滑块，匹配相同验证。"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from slider_solver.config import RECORDS_DIR
from slider_solver.screen_match import Region, grab_region, save_region_image


@dataclass
class SliderRecord:
    id: str
    name: str
    captcha_region: dict
    captcha_image: str
    knob_template: str
    drag_distance: int
    start_x: int
    start_y: int
    duration_ms: int
    created_at: str
    match_threshold: float = 0.88

    @classmethod
    def from_dict(cls, d: dict) -> SliderRecord:
        return cls(
            id=d["id"],
            name=d.get("name", ""),
            captcha_region=d["captcha_region"],
            captcha_image=d["captcha_image"],
            knob_template=d["knob_template"],
            drag_distance=int(d["drag_distance"]),
            start_x=int(d["start_x"]),
            start_y=int(d["start_y"]),
            duration_ms=int(d.get("duration_ms", 900)),
            created_at=d.get("created_at", ""),
            match_threshold=float(d.get("match_threshold", 0.88)),
        )


@dataclass
class MatchHit:
    record: SliderRecord
    score: float


def _read_bgr(path: str | Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"无法读取: {path}")
    return img


def _similarity(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        b = cv2.resize(b, (a.shape[1], a.shape[0]))
    res = cv2.matchTemplate(a, b, cv2.TM_CCOEFF_NORMED)
    return float(res.max())


def list_records() -> list[SliderRecord]:
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    out: list[SliderRecord] = []
    for meta in sorted(RECORDS_DIR.glob("*/meta.json")):
        try:
            d = json.loads(meta.read_text(encoding="utf-8"))
            out.append(SliderRecord.from_dict(d))
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    return out


def save_record(
    *,
    region: Region,
    captcha_bgr: np.ndarray,
    knob_bgr: np.ndarray,
    drag_distance: int,
    start_x: int,
    start_y: int,
    duration_ms: int = 900,
    name: str = "",
) -> SliderRecord:
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    rid = uuid.uuid4().hex[:10]
    folder = RECORDS_DIR / rid
    folder.mkdir(parents=True, exist_ok=True)

    cap_path = folder / "captcha.png"
    knob_path = folder / "knob.png"
    cv2.imencode(".png", captcha_bgr)[1].tofile(str(cap_path))
    cv2.imencode(".png", knob_bgr)[1].tofile(str(knob_path))

    rec = SliderRecord(
        id=rid,
        name=name or f"记录_{datetime.now().strftime('%m%d_%H%M')}",
        captcha_region=region.as_dict(),
        captcha_image=str(cap_path),
        knob_template=str(knob_path),
        drag_distance=int(drag_distance),
        start_x=int(start_x),
        start_y=int(start_y),
        duration_ms=int(duration_ms),
        created_at=datetime.now().isoformat(timespec="seconds"),
    )
    (folder / "meta.json").write_text(
        json.dumps(asdict(rec), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return rec


def match_record(
    region: Region,
    *,
    threshold: float | None = None,
) -> MatchHit | None:
    current = grab_region(region)
    best: MatchHit | None = None
    for rec in list_records():
        if not Path(rec.captcha_image).is_file():
            continue
        saved = _read_bgr(rec.captcha_image)
        score = _similarity(current, saved)
        th = threshold if threshold is not None else rec.match_threshold
        if score >= th and (best is None or score > best.score):
            best = MatchHit(record=rec, score=score)
    return best


def crop_knob_patch(bgr: np.ndarray, cx: int, cy: int, size: int = 48) -> np.ndarray:
    h, w = bgr.shape[:2]
    half = size // 2
    x1 = max(0, cx - half)
    y1 = max(0, cy - half)
    x2 = min(w, cx + half)
    y2 = min(h, cy + half)
    return bgr[y1:y2, x1:x2].copy()
