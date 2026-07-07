"""识别当前是第1步还是第2步。"""
from __future__ import annotations

from slider_solver.screen_match import Region, grab_region
from verify_auto.step1_pick import ocr_image


def detect_step(prompt_region: Region | None, full_region: Region | None = None) -> int:
    """返回 1 / 2 / 0(未知)。"""
    region = prompt_region or full_region
    if not region:
        return 0
    img = grab_region(region)
    text = ocr_image(img)
    if "运动最慢" in text or "最慢的元素" in text:
        return 2
    if "选择最符合" in text or "描述的图片" in text:
        return 1
    return 0
