"""把配置解析成当前屏幕上的实际区域。"""
from __future__ import annotations

from dataclasses import dataclass

from slider_solver.screen_match import Region

from verify_auto.locate_cache import get_cached, put_cache
from verify_auto.window_locate import find_anchor_on_screen, regions_from_profile, union_search_region


@dataclass
class CaptchaRegions:
    prompt: Region
    grid: Region
    ball: Region
    search: Region
    auto: bool
    anchor_text: str = ""


@dataclass
class ResolveResult:
    ok: bool
    message: str
    regions: CaptchaRegions | None = None
    cached: bool = False


def _fixed_regions(cfg: dict) -> CaptchaRegions | None:
    prompt = Region.from_dict(cfg.get("prompt_region"))
    grid = Region.from_dict(cfg.get("grid_region"))
    ball = Region.from_dict(cfg.get("step2_ball_region"))
    if not prompt or not grid or not ball:
        return None
    search = union_search_region(prompt, grid, ball) or prompt
    return CaptchaRegions(prompt=prompt, grid=grid, ball=ball, search=search, auto=False)


def resolve_regions_learn(cfg: dict, *, step_hint: int = 0, force_relocate: bool = False) -> ResolveResult:
    """学习模式：优先固定坐标，仅在需要时全屏定位。"""
    fixed = _fixed_regions(cfg)
    if fixed and not force_relocate:
        return ResolveResult(True, "学习：固定区域", fixed)

    if force_relocate or not fixed:
        return resolve_regions(cfg, step_hint=step_hint, force_refresh=force_relocate)

    return ResolveResult(True, "学习：固定区域", fixed)


def resolve_regions(cfg: dict, *, step_hint: int = 0, force_refresh: bool = False) -> ResolveResult:
    """优先缓存；需要时才全屏 OCR 定位。"""
    from verify_auto.locate_cache import mark_full_locate, should_full_locate

    if not force_refresh:
        hit = get_cached()
        if hit:
            return ResolveResult(True, f"缓存定位 {hit.message}", hit.regions, cached=True)

    do_full = force_refresh or should_full_locate()
    if not do_full:
        hit = get_cached(max_age=60.0)
        if hit:
            return ResolveResult(True, f"缓存定位 {hit.message}", hit.regions, cached=True)

    use_auto = bool(cfg.get("auto_locate", True))
    profile = cfg.get("layout_profile")

    if use_auto and profile:
        anchor = find_anchor_on_screen(step_hint=step_hint)
        if anchor:
            mark_full_locate()
            prompt, grid, ball = regions_from_profile(profile, anchor)
            search = union_search_region(prompt, grid, ball) or prompt
            result = ResolveResult(
                True,
                f"已自动定位小窗 @ ({prompt.left},{prompt.top})",
                CaptchaRegions(
                    prompt=prompt,
                    grid=grid,
                    ball=ball,
                    search=search,
                    auto=True,
                    anchor_text=anchor.text,
                ),
            )
            put_cache(result)
            return result

    fixed = _fixed_regions(cfg)
    if fixed:
        msg = "自动定位失败，已回退固定坐标" if use_auto and profile else "使用固定坐标"
        result = ResolveResult(True, msg, fixed)
        put_cache(result)
        return result

    if not profile:
        return ResolveResult(False, "请先框选：提示区 + 网格区 + 球区（各框一次即可，以后自动跟位置）")
    return ResolveResult(False, "未找到验证小窗。请先弹出验证码，或重新框选区域")
