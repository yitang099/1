"""词库内存缓存 — 启动时预加载，匹配时不再反复读盘。"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from verify_auto.library_store import (
    STEP1_DIR,
    STEP2_SCENES_DIR,
    STEP2_TAGS_DIR,
    _similarity,
    list_step1_keywords,
    list_step2_tags,
    step1_keyword_dir,
    step2_tag_dir,
)

_IMG_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
_lock = threading.Lock()
_loaded = False
_step1_refs: list[tuple[str, str, np.ndarray]] = []  # keyword, filename, bgr
_step2_slow_refs: list[tuple[str, np.ndarray]] = []
_step2_scenes: list[tuple[np.ndarray, dict]] = []


def _read_img(path: Path) -> np.ndarray | None:
    if path.suffix.lower() not in _IMG_EXTS:
        return None
    img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    return img


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
                    s1.append((kw, p.name, img))

        slow: list[tuple[str, np.ndarray]] = []
        for tag in ("慢球",):
            d = step2_tag_dir(tag)
            if not d.is_dir():
                continue
            for p in d.iterdir():
                img = _read_img(p)
                if img is not None:
                    slow.append((p.name, img))

        scenes: list[tuple[np.ndarray, dict]] = []
        if STEP2_SCENES_DIR.is_dir():
            import json

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
    min_score: float = 0.62,
) -> tuple[int, float, str, str] | None:
    """返回最佳 (格子序号, 分数, 关键词, 参考图名)。"""
    load_library_cache()
    with _lock:
        refs = _step1_refs
    if not refs:
        return None

    best: tuple[int, float, str, str] | None = None
    kw = keyword.strip()

    for i, cell in enumerate(cells):
        for ref_kw, ref_name, ref_img in refs:
            if kw and ref_kw != kw and kw not in ref_kw and ref_kw not in kw:
                continue
            score = _similarity(cell, ref_img)
            if score < min_score:
                continue
            if best is None or score > best[1]:
                best = (i, score, ref_kw, ref_name)
    return best


def match_step1_global(cells: list[np.ndarray], *, min_score: float = 0.60) -> tuple[int, float, str, str] | None:
    return match_step1_best(cells, keyword="", min_score=min_score)


def get_step2_cache() -> tuple[list[tuple[np.ndarray, dict]], list[tuple[str, np.ndarray]]]:
    load_library_cache()
    with _lock:
        return list(_step2_scenes), list(_step2_slow_refs)
