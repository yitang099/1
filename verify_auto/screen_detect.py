"""识别当前是第1步还是第2步（带缓存，降低 CPU）。"""
from __future__ import annotations

import time

from slider_solver.screen_match import Region, grab_region
from verify_auto.layout_profile import STEP1_ANCHORS, STEP2_ANCHORS
from verify_auto.ocr_util import find_anchor_line, ocr_lines, ocr_text
from verify_auto.step1_pick import ocr_image

_step_cache: dict = {"ts": 0.0, "step": 0, "key": None}
STEP_CACHE_SEC = 2.5


def _region_key(region: Region) -> tuple:
    return (region.left, region.top, region.width, region.height)


def _norm(text: str) -> str:
    return text.replace(" ", "").replace("\n", "")


def _parse_step(text: str) -> int:
    t = _norm(text)
    if any(k in t for k in ("运动最慢", "最慢的元素", "请点击运动")):
        return 2
    if "请点击" in t and "最慢" in t:
        return 2
    if any(k in t for k in ("选择最符合", "描述的图片", "最符合描述")):
        return 1
    return 0


def _step_from_lines(lines) -> tuple[int, str]:
    """逐行锚点匹配，第2步优先。"""
    hit2 = find_anchor_line(lines, list(STEP2_ANCHORS))
    if hit2:
        return 2, hit2.text
    hit1 = find_anchor_line(lines, list(STEP1_ANCHORS))
    if hit1:
        return 1, hit1.text
    joined = " ".join(line.text for line in lines)
    step = _parse_step(joined)
    return step, joined


def _text_from_region(region: Region | None) -> str:
    if not region:
        return ""
    return ocr_text(grab_region(region))


def _detect_from_region(region: Region | None) -> tuple[int, str]:
    if not region:
        return 0, ""
    img = grab_region(region)
    lines = ocr_lines(img)
    step, text = _step_from_lines(lines)
    if step:
        return step, text
    joined = ocr_text(img)
    return _parse_step(joined), joined


def ocr_prompt_text(prompt_region: Region | None) -> str:
    if not prompt_region:
        return ""
    return ocr_image(grab_region(prompt_region))


def detect_step(
    step1_prompt: Region | None,
    step2_prompt: Region | None = None,
    full_region: Region | None = None,
) -> int:
    """返回 1 / 2 / 0(未知)。优先查第2步文字区。"""
    for region in (step2_prompt, step1_prompt, full_region):
        if not region:
            continue
        step, _ = _detect_from_region(region)
        if step:
            return step
    return 0


def detect_step_fast(prompt_region: Region | None) -> tuple[int, str]:
    if not prompt_region:
        return 0, ""
    return _detect_from_region(prompt_region)


def detect_step_for_learn(
    step1_prompt: Region | None,
    step2_prompt: Region | None,
    search_region: Region | None = None,
) -> tuple[int, str, bool]:
    """学习模式：先查第2步文字区，再查第1步文字区，最后整块验证区。"""
    last_text = ""
    for region in (step2_prompt, step1_prompt, search_region):
        if not region:
            continue
        step, text = _detect_from_region(region)
        if text:
            last_text = text
        if step:
            return step, text, False
    return 0, last_text, not last_text


def invalidate_step_cache() -> None:
    _step_cache["ts"] = 0.0
