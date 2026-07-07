"""校验识别框是否对准当前验证码小窗。"""
from __future__ import annotations

from slider_solver.screen_match import grab_region
from verify_auto.layout_profile import STEP1_ANCHORS, STEP2_ANCHORS
from verify_auto.ocr_util import find_anchor_line, ocr_lines
from verify_auto.region_resolve import CaptchaRegions
from verify_auto.screen_detect import detect_step


def _anchor_in_region(region, anchors: tuple[str, ...]) -> bool:
    if not region:
        return False
    img = grab_region(region)
    if img is None or img.size == 0:
        return False
    return find_anchor_line(ocr_lines(img), list(anchors)) is not None


def validate_regions(regions: CaptchaRegions, *, step_hint: int = 0) -> tuple[bool, str]:
    """检查提示区 OCR 是否含对应步骤锚点文字。"""
    step = detect_step(regions.step1_prompt, regions.step2_prompt, regions.search)
    if step == 0:
        return False, "识别框内读不到验证码文字（框位置偏了）"

    if step_hint == 2 or step == 2:
        if _anchor_in_region(regions.step2_prompt, STEP2_ANCHORS):
            return True, f"第2步校验通过 step={step}"
        if _anchor_in_region(regions.search, STEP2_ANCHORS):
            return True, f"第2步校验通过(整块) step={step}"

    if step_hint == 1 or step == 1:
        if _anchor_in_region(regions.step1_prompt, STEP1_ANCHORS):
            return True, f"第1步校验通过 step={step}"
        if _anchor_in_region(regions.search, STEP1_ANCHORS):
            return True, f"第1步校验通过(整块) step={step}"

    if _anchor_in_region(regions.search, STEP2_ANCHORS + STEP1_ANCHORS):
        return True, f"校验通过 step={step}"
    return False, f"锚点不在框内 step={step}（识别框偏移）"
