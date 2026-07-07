"""词库极速：只点一次，不乱试，不逐格试探。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from slider_solver.screen_match import grab_region
from verify_auto.ball_slowest import find_slowest_moving_ball
from verify_auto.captcha_detect import auto_detect_regions
from verify_auto.click_util import click_screen
from verify_auto.confirm_click import click_confirm_smart
from verify_auto.library_cache import library_stats, load_library_cache, match_step1_best
from verify_auto.locate_cache import get_cached, put_cache
from verify_auto.region_resolve import CaptchaRegions, ResolveResult, _fixed_regions, _resolve_auto
from verify_auto.screen_detect import detect_step
from verify_auto.step1_keyword import extract_keyword_from_region
from verify_auto.step1_pick import cell_centers, split_grid
from verify_auto.step2_library import find_slow_ball_fast


@dataclass
class FastResult:
    ok: bool
    message: str
    step: int = 0
    actions: list[str] = field(default_factory=list)


def _log(actions: list[str], msg: str, on_progress: Callable[[str], None] | None) -> None:
    if msg:
        actions.append(msg)
        if on_progress:
            on_progress(msg)


def _cache(regions: CaptchaRegions, msg: str) -> None:
    put_cache(ResolveResult(True, msg, regions))


def resolve_fast(cfg: dict, *, step_hint: int = 0) -> tuple[CaptchaRegions | None, str]:
    hit = get_cached(max_age=300.0)
    if hit and hit.regions:
        return hit.regions, "[缓存]"

    if cfg.get("layout_profile"):
        auto = _resolve_auto(cfg, step_hint=step_hint)
        if auto:
            _cache(auto, "layout")
            return auto, f"[布局] ({auto.step1_prompt.left},{auto.step1_prompt.top})"

    fixed = _fixed_regions(cfg)
    if fixed:
        _cache(fixed, "fixed")
        return fixed, "[框选]"

    auto = auto_detect_regions(step_hint=step_hint or 1)
    if auto:
        _cache(auto, "auto")
        return auto, f"[找窗] ({auto.step1_prompt.left},{auto.step1_prompt.top})"
    return None, "未找到验证小窗，请先弹出验证码"


def _keyword(regions: CaptchaRegions, override: str) -> str:
    if override.strip():
        return override.strip()
    kw, _ = extract_keyword_from_region(regions.step1_prompt)
    if kw:
        return kw
    kw, _ = extract_keyword_from_region(regions.search)
    return kw


def _pick_step1(
    cfg: dict,
    regions: CaptchaRegions,
    *,
    keyword_override: str,
    actions: list[str],
    on_progress: Callable[[str], None] | None,
) -> tuple[bool, str]:
    min_score = float(cfg.get("fast_min_score") or 0.70)
    cells = split_grid(grab_region(regions.grid))
    kw = _keyword(regions, keyword_override)

    if not kw:
        return False, "未读到关键词：请在参数栏填写（如 柠檬），或框选第1步文字区"

    _log(actions, f"[第1步] 关键词「{kw}」→ 词库匹配…", on_progress)
    hit = match_step1_best(cells, keyword=kw, min_score=min_score)
    if not hit:
        return False, f"词库「{kw}」未匹配到（分数<{min_score:.2f}）。请多收录几张或降低 fast_min_score"

    cell_i, score, lib_kw, ref = hit
    cx, cy = cell_centers(regions.grid)[cell_i]
    _log(actions, f"[第1步] 第{cell_i + 1}格 score={score:.2f} ref={ref}", on_progress)

    bg = bool(cfg.get("background_click", True))
    click_screen(cx, cy, background=bg)
    time.sleep(0.15)
    if not click_confirm_smart(cfg, regions.search):
        return False, "未点到确定（请框选一次蓝色确定按钮）"
    return True, lib_kw


def _wait_step2(cfg: dict, actions: list[str], on_progress: Callable[[str], None] | None) -> CaptchaRegions | None:
    deadline = time.time() + float(cfg.get("fast_step2_wait") or 1.8)
    while time.time() < deadline:
        regions, _ = resolve_fast(cfg, step_hint=2)
        if regions and detect_step(regions.step2_prompt, regions.step1_prompt, regions.search) == 2:
            return regions
        time.sleep(0.15)
    return None


def _pick_step2(
    cfg: dict,
    regions: CaptchaRegions,
    *,
    actions: list[str],
    on_progress: Callable[[str], None] | None,
) -> bool:
    regions, loc = resolve_fast(cfg, step_hint=2)
    _log(actions, loc, on_progress)
    area = regions.ball or regions.grid
    bg = bool(cfg.get("background_click", True))

    lib = find_slow_ball_fast(area, min_score=0.52)
    if lib:
        x, y, score, method = lib
        _log(actions, f"[第2步] {method} ({x},{y}) score={score:.2f}", on_progress)
        click_screen(x, y, background=bg)
        time.sleep(0.15)
        if click_confirm_smart(cfg, regions.search):
            return True

    _log(actions, "[第2步] 词库未中，6帧追踪最慢球…", on_progress)
    r = find_slowest_moving_ball(
        area,
        frames=int(cfg.get("fast_ball_frames") or 6),
        interval_ms=int(cfg.get("fast_ball_interval_ms") or 60),
    )
    if not r.ok:
        return False
    click_screen(r.click_x, r.click_y, background=bg)
    time.sleep(0.15)
    return click_confirm_smart(cfg, regions.search)


def run_fast_agent(
    cfg: dict,
    *,
    keyword_override: str = "",
    on_progress: Callable[[str], None] | None = None,
) -> FastResult:
    actions: list[str] = []
    load_library_cache()
    stats = library_stats()
    _log(
        actions,
        f"词库 {stats['step1_images']} 张 / {stats['step1_keywords']} 词 | 慢球 {stats['step2_slow_images']} 张",
        on_progress,
    )
    if not stats["ready"]:
        return FastResult(False, "第1步词库为空，请先收录图片", actions=actions)

    regions, loc = resolve_fast(cfg)
    if not regions:
        return FastResult(False, loc, actions=actions)
    _log(actions, loc, on_progress)

    step = detect_step(regions.step1_prompt, regions.step2_prompt, regions.search) or 1

    if step == 1:
        ok, msg = _pick_step1(cfg, regions, keyword_override=keyword_override, actions=actions, on_progress=on_progress)
        if not ok:
            return FastResult(False, msg, step=1, actions=actions)
        regions = _wait_step2(cfg, actions, on_progress)
        if not regions:
            return FastResult(False, "第1步后未出现第2步", step=1, actions=actions)

    if not _pick_step2(cfg, regions, actions=actions, on_progress=on_progress):
        return FastResult(False, "第2步失败", step=2, actions=actions)

    _log(actions, "[完成] ✓", on_progress)
    return FastResult(True, "验证已通过", step=2, actions=actions)
