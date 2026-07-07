"""把配置解析成当前屏幕上的实际区域。"""
from __future__ import annotations

from dataclasses import dataclass

from slider_solver.screen_match import Region

from verify_auto.layout_profile import update_layout_profile
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


def _fixed_regions(cfg: dict) -> CaptchaRegions | None:
    prompt = Region.from_dict(cfg.get("prompt_region"))
    grid = Region.from_dict(cfg.get("grid_region"))
    ball = Region.from_dict(cfg.get("step2_ball_region"))
    if not prompt or not grid or not ball:
        return None
    search = union_search_region(prompt, grid, ball) or prompt
    return CaptchaRegions(prompt=prompt, grid=grid, ball=ball, search=search, auto=False)


def resolve_regions(cfg: dict, *, step_hint: int = 0) -> ResolveResult:
    """优先自动定位；失败则回退到固定坐标。"""
    use_auto = bool(cfg.get("auto_locate", True))
    profile = cfg.get("layout_profile")

    if use_auto and profile:
        anchor = find_anchor_on_screen(step_hint=step_hint)
        if anchor:
            prompt, grid, ball = regions_from_profile(profile, anchor)
            search = union_search_region(prompt, grid, ball) or prompt
            return ResolveResult(
                True,
                f"已自动定位小窗 @ ({prompt.left},{prompt.top}) 「{anchor.text[:20]}」",
                CaptchaRegions(
                    prompt=prompt,
                    grid=grid,
                    ball=ball,
                    search=search,
                    auto=True,
                    anchor_text=anchor.text,
                ),
            )

    fixed = _fixed_regions(cfg)
    if fixed:
        if use_auto and profile:
            return ResolveResult(
                True,
                "自动定位失败，已回退固定坐标（请确认验证小窗已弹出）",
                fixed,
            )
        return ResolveResult(True, "使用固定坐标", fixed)

    if not profile:
        return ResolveResult(False, "请先框选：提示区 + 网格区 + 球区（各框一次即可，以后自动跟位置）")
    return ResolveResult(False, "未找到验证小窗。请先弹出验证码，或重新框选区域")


def ensure_layout_profile(cfg: dict) -> bool:
    return update_layout_profile(cfg)
