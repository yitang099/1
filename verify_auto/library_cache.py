"""词库内存缓存 — 预加载 + 归一化匹配。"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import cv2
import numpy as np

from verify_auto.library_store import (
    STEP2_SCENES_DIR,
    list_step1_keywords,
    step1_keyword_dir,
    step2_tag_dir,
)

_IMG_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
_CELL_SIZE = (96, 96)
_lock = threading.Lock()
_loaded = False
_step1_refs: list[tuple[str, str, np.ndarray]] = []
_step2_slow_refs: list[tuple[str, np.ndarray]] = []
_step2_scenes: list[tuple[np.ndarray, dict]] = []


def _read_img(path: Path) -> np.ndarray | None:
    if path.suffix.lower() not in _IMG_EXTS:
        return None
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)


def _norm(bgr: np.ndarray) -> np.ndarray:
    return cv2.resize(bgr, _CELL_SIZE, interpolation=cv2.INTER_AREA)


def _sim(a: np.ndarray, b: np.ndarray) -> float:
    a2, b2 = _norm(a), _norm(b)
    res = cv2.matchTemplate(a2, b2, cv2.TM_CCOEFF_NORMED)
    return float(res.max()) if res.size else 0.0


def load_library_cache(*, force: bool = False) -> None:
    global _loaded, _step1_refs, _step2_slow_refs, _step2_scenes
    with _lock:
        if _loaded and not force:
            return
        s1: list[tuple[str, str, np.ndarray]] = []
        for kw in list_step1_keywords():
            for p in step1_keyword_dir(kw).iterdir():
                img = _read_img(p)
                if img is not None:
                    s1.append((kw, p.name, _norm(img)))

        slow: list[tuple[str, np.ndarray]] = []
        d = step2_tag_dir("慢球")
        if d.is_dir():
            for p in d.iterdir():
                img = _read_img(p)
                if img is not None:
                    slow.append((p.name, _norm(img)))

        scenes: list[tuple[np.ndarray, dict]] = []
        if STEP2_SCENES_DIR.is_dir():
            for jp in STEP2_SCENES_DIR.glob("*.json"):
                png = jp.with_suffix(".png")
                if not png.is_file():
                    continue
                img = _read_img(png)
                if img is None:
                    continue
                try:
                    meta = json.loads(jp.read_text(encoding="utf-8"))
                except Exception:
                    meta = {}
                scenes.append((img, meta))

        _step1_refs = s1
        _step2_slow_refs = slow
        _step2_scenes = scenes
        _loaded = True


def invalidate_library_cache() -> None:
    global _loaded
    with _lock:
        _loaded = False


def library_stats() -> dict:
    load_library_cache()
    with _lock:
        kws = {k for k, _, _ in _step1_refs}
        return {
            "step1_keywords": len(kws),
            "step1_images": len(_step1_refs),
            "step2_slow_images": len(_step2_slow_refs),
            "step2_scenes": len(_step2_scenes),
            "ready": len(_step1_refs) > 0,
        }


def match_step1_best(
    cells: list[np.ndarray],
    *,
    keyword: str = "",
    min_score: float = 0.70,
) -> tuple[int, float, str, str] | None:
    load_library_cache()
    with _lock:
        refs = list(_step1_refs)
    if not refs:
        return None

    kw = keyword.strip()
    ranked: list[tuple[int, float, str, str]] = []
    norms = [_norm(c) for c in cells]

    for i, cell_n in enumerate(norms):
        for ref_kw, ref_name, ref_n in refs:
            if kw and ref_kw != kw:
                continue
            score = float(cv2.matchTemplate(cell_n, ref_n, cv2.TM_CCOEFF_NORMED).max())
            if score >= min_score:
                ranked.append((i, score, ref_kw, ref_name))

    if not ranked:
        return None
    ranked.sort(key=lambda x: x[1], reverse=True)
    best = ranked[0]
    if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < 0.06:
        return None
    return best


def get_step2_cache() -> tuple[list[tuple[np.ndarray, dict]], list[tuple[str, np.ndarray]]]:
    load_library_cache()
    with _lock:
        return list(_step2_scenes), list(_step2_slow_refs)
