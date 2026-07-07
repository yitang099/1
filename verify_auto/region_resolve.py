"""把配置解析成当前屏幕上的实际区域。"""
from __future__ import annotations

from dataclasses import dataclass

from slider_solver.screen_match import Region

from verify_auto.locate_cache import get_cached, put_cache
from verify_auto.window_locate import find_anchor_on_screen, regions_from_profile, union_search_region


@dataclass
class CaptchaRegions:
    step1_prompt: Region
    step2_prompt: Region
    grid: Region
    ball: Region
    search: Region
    auto: bool
    anchor_text: str = ""

    @property
    def prompt(self) -> Region:
        """兼容旧代码：默认第1步提示区。"""
        return self.step1_prompt

    def prompt_for(self, step: int) -> Region:
        return self.step2_prompt if step == 2 else self.step1_prompt


@dataclass
class ResolveResult:
    ok: bool
    message: str
    regions: CaptchaRegions | None = None
    cached: bool = False


def _prompt_from_cfg(cfg: dict) -> tuple[Region | None, Region | None]:
    s1 = Region.from_dict(cfg.get("step1_prompt_region") or cfg.get("prompt_region"))
    s2 = Region.from_dict(cfg.get("step2_prompt_region") or s1)
    return s1, s2


def _make_regions(
    step1_prompt: Region,
    step2_prompt: Region,
    grid: Region,
    ball: Region,
    *,
    auto: bool,
    anchor_text: str = "",
) -> CaptchaRegions:
    search = union_search_region(step1_prompt, step2_prompt, grid, ball) or step1_prompt
    return CaptchaRegions(
        step1_prompt=step1_prompt,
        step2_prompt=step2_prompt,
        grid=grid,
        ball=ball,
        search=search,
        auto=auto,
        anchor_text=anchor_text,
    )


def _fixed_regions(cfg: dict) -> CaptchaRegions | None:
    s1, s2 = _prompt_from_cfg(cfg)
    grid = Region.from_dict(cfg.get("grid_region"))
    ball = Region.from_dict(cfg.get("step2_ball_region"))
    if not s1 or not s2 or not grid or not ball:
        return None
    return _make_regions(s1, s2, grid, ball, auto=False)


def _resolve_auto(cfg: dict, *, step_hint: int = 0) -> ResolveResult | None:
    profile = cfg.get("layout_profile")
    if not profile:
        return None
    anchor = find_anchor_on_screen(step_hint=step_hint)
    if not anchor:
        return None
    s1, s2, grid, ball = regions_from_profile(profile, anchor, step_hint=step_hint)
    return _make_regions(s1, s2, grid, ball, auto=True, anchor_text=anchor.text)


def resolve_regions_learn(cfg: dict, *, step_hint: int = 0, force_relocate: bool = False) -> ResolveResult:
    """学习模式：验证码会随机位置，优先全屏 OCR 自动定位。"""
    from verify_auto.locate_cache import mark_full_locate, put_cache

    use_auto = bool(cfg.get("auto_locate", True))
    if use_auto:
        hit = _resolve_auto(cfg, step_hint=step_hint)
        if hit:
            mark_full_locate()
            result = ResolveResult(
                True,
                f"学习定位 @ ({hit.step1_prompt.left},{hit.step1_prompt.top}) 「{hit.anchor_text[:14]}」",
                hit,
            )
            put_cache(result)
            return result
        if force_relocate:
            return resolve_regions(cfg, step_hint=step_hint, force_refresh=True)

    fixed = _fixed_regions(cfg)
    if fixed:
        return ResolveResult(True, "学习：固定区域（全屏未找到验证字）", fixed)

    if not cfg.get("layout_profile"):
        return ResolveResult(
            False,
            "请先框选：第1步文字 + 网格 + 第2步文字 + 球区（各框一次）",
        )
    return ResolveResult(False, "未找到验证小窗。请先弹出验证码，或重新框选区域")


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
    if use_auto:
        hit = _resolve_auto(cfg, step_hint=step_hint)
        if hit:
            mark_full_locate()
            result = ResolveResult(
                True,
                f"已自动定位小窗 @ ({hit.step1_prompt.left},{hit.step1_prompt.top})",
                hit,
            )
            put_cache(result)
            return result

    fixed = _fixed_regions(cfg)
    if fixed:
        msg = "自动定位失败，已回退固定坐标" if use_auto and cfg.get("layout_profile") else "使用固定坐标"
        result = ResolveResult(True, msg, fixed)
        put_cache(result)
        return result

    if not cfg.get("layout_profile"):
        return ResolveResult(False, "请先框选：第1步文字 + 网格 + 第2步文字 + 球区（各框一次）")
    return ResolveResult(False, "未找到验证小窗。请先弹出验证码，或重新框选区域")
