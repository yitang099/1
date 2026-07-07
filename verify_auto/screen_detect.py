"""识别当前是第1步还是第2步（带缓存，降低 CPU）。"""
from __future__ import annotations

import time

from slider_solver.screen_match import Region, grab_region
from verify_auto.ocr_util import ocr_text
from verify_auto.step1_pick import ocr_image

_step_cache: dict = {"ts": 0.0, "step": 0, "key": None}
STEP_CACHE_SEC = 2.5


def _region_key(region: Region) -> tuple:
    return (region.left, region.top, region.width, region.height)


def _parse_step(text: str) -> int:
    if "运动最慢" in text or "最慢的元素" in text or "请点击" in text and "最慢" in text:
        return 2
    if "选择最符合" in text or "描述的图片" in text or "最符合" in text:
        return 1
    return 0


def _text_from_region(region: Region | None) -> str:
    if not region:
        return ""
    return ocr_text(grab_region(region))


def ocr_prompt_text(prompt_region: Region | None) -> str:
    if not prompt_region:
        return ""
    return ocr_image(grab_region(prompt_region))


def detect_step(prompt_region: Region | None, full_region: Region | None = None) -> int:
    """返回 1 / 2 / 0(未知)。"""
    region = prompt_region or full_region
    if not region:
        return 0

    key = _region_key(region)
    now = time.time()
    if _step_cache.get("key") == key and now - float(_step_cache.get("ts") or 0) < STEP_CACHE_SEC:
        return int(_step_cache.get("step") or 0)

    text = ocr_prompt_text(region)
    step = _parse_step(text)
    _step_cache.update(ts=now, step=step, key=key)
    return step


def detect_step_fast(prompt_region: Region | None) -> tuple[int, str]:
    """学习模式：OCR 提示区，不走缓存。"""
    if not prompt_region:
        return 0, ""
    text = ocr_prompt_text(prompt_region)
    return _parse_step(text), text


def detect_step_for_learn(
    prompt_region: Region | None,
    search_region: Region | None = None,
) -> tuple[int, str, bool]:
    """学习模式：先 OCR 提示区，再 OCR 整块验证区。无字则建议重新定位。"""
    last_text = ""
    for region in (prompt_region, search_region):
        if not region:
            continue
        text = _text_from_region(region)
        if text:
            last_text = text
        step = _parse_step(text)
        if step:
            return step, text, False
    return 0, last_text, not last_text


def invalidate_step_cache() -> None:
    _step_cache["ts"] = 0.0
