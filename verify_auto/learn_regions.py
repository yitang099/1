"""学习模式区域解析：优先固定坐标，少做全屏 OCR。"""
from __future__ import annotations

from verify_auto.region_resolve import (
    CaptchaRegions,
    ResolveResult,
    _fixed_regions,
    _make_regions,
    _resolve_auto,
)
from verify_auto.locate_cache import mark_full_locate, put_cache


def resolve_regions_learn(
    cfg: dict,
    *,
    step_hint: int = 0,
    force_relocate: bool = False,
    silent: bool = False,
) -> ResolveResult:
    """收录模式：默认用已框选的固定坐标；仅必要时全屏定位。"""
    fixed = _fixed_regions(cfg)
    if fixed and not force_relocate:
        msg = "" if silent else "使用已框选区域"
        return ResolveResult(True, msg, fixed)

    if cfg.get("ai_auto_no_calibrate", True) and (force_relocate or not fixed):
        from verify_auto.captcha_detect import auto_detect_regions

        auto = auto_detect_regions(step_hint=step_hint)
        if auto:
            msg = "" if silent else f"AI 自动定位 @ ({auto.step1_prompt.left},{auto.step1_prompt.top})"
            return ResolveResult(True, msg, auto)

    use_auto = bool(cfg.get("auto_locate", True))
    profile = cfg.get("layout_profile")
    if use_auto and profile and (force_relocate or not fixed):
        hit = _resolve_auto(cfg, step_hint=step_hint)
        if hit:
            mark_full_locate()
            msg = (
                f"学习定位 @ ({hit.step1_prompt.left},{hit.step1_prompt.top})"
                if not silent
                else ""
            )
            result = ResolveResult(True, msg, hit)
            put_cache(result)
            return result

    if fixed:
        return ResolveResult(True, "使用已框选区域", fixed)

    if not profile:
        return ResolveResult(
            False,
            "请先框选：第1步文字 + 网格 + 第2步文字 + 球区",
        )
    return ResolveResult(False, "未找到验证小窗，请先弹出验证码")
