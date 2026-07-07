"""词库极速模式：缓存定位 + 预加载案例 + 关键词匹配 + 一键过验证。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from slider_solver.screen_match import grab_region
from verify_auto.ball_slowest import find_slowest_in_areas
from verify_auto.captcha_detect import auto_detect_regions
from verify_auto.click_util import click_screen
from verify_auto.confirm_click import click_confirm_button
from verify_auto.library_cache import library_stats, load_library_cache, match_step1_best, match_step1_global
from verify_auto.locate_cache import get_cached, put_cache
from verify_auto.region_resolve import CaptchaRegions, ResolveResult, _fixed_regions, _resolve_auto
from verify_auto.screen_detect import detect_step
from verify_auto.selection_marker import detect_step2_selected_from_region
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
    """极速找窗：缓存 → 布局 → 小窗附近 OCR（跳过多轮全屏扫描）。"""
    hit = get_cached(max_age=120.0)
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
        return fixed, "[框选区域]"

    auto = auto_detect_regions(step_hint=step_hint or 1)
    if auto:
        _cache(auto, "auto")
        return auto, f"[找窗] ({auto.step1_prompt.left},{auto.step1_prompt.top})"

    auto = auto_detect_regions(step_hint=2)
    if auto:
        _cache(auto, "auto")
        return auto, f"[找窗] ({auto.step1_prompt.left},{auto.step1_prompt.top})"

    return None, "未找到验证小窗，请先弹出验证码"


def _quick_keyword(regions: CaptchaRegions, override: str) -> str:
    if override.strip():
        return override.strip()
    kw, _ = extract_keyword_from_region(regions.step1_prompt)
    if kw:
        return kw
    kw, _ = extract_keyword_from_region(regions.search)
    return kw


def _pick_step1_fast(
    cfg: dict,
    regions: CaptchaRegions,
    *,
    keyword_override: str,
    actions: list[str],
    on_progress: Callable[[str], None] | None,
) -> tuple[bool, str]:
    min_score = float(cfg.get("fast_min_score") or cfg.get("step1_min_score") or 0.62)
    grid_img = grab_region(regions.grid)
    cells = split_grid(grid_img)
    centers = cell_centers(regions.grid)
    kw = _quick_keyword(regions, keyword_override)

    if kw:
        _log(actions, f"[第1步] 关键词「{kw}」", on_progress)
        hit = match_step1_best(cells, keyword=kw, min_score=min_score)
    else:
        _log(actions, "[第1步] OCR未读到词，全库匹配…", on_progress)
        hit = match_step1_global(cells, min_score=min_score - 0.02)

    if not hit:
        hit = match_step1_global(cells, min_score=min_score - 0.04)

    if not hit:
        return False, "词库未匹配到（请确认已收录该关键词的图片）"

    cell_i, score, lib_kw, ref = hit
    cx, cy = centers[cell_i]
    _log(actions, f"[第1步] 词库「{lib_kw}」→ 第{cell_i + 1}格 ({score:.2f}) {ref}", on_progress)

    bg = bool(cfg.get("background_click", True))
    click_screen(cx, cy, background=bg)
    time.sleep(0.22)
    if not click_confirm_button(cfg, regions.search):
        time.sleep(0.1)
        click_confirm_button(cfg, regions.search)
    return True, lib_kw


def _wait_step2_fast(cfg: dict, actions: list[str], on_progress: Callable[[str], None] | None) -> CaptchaRegions | None:
    wait = float(cfg.get("fast_step2_wait") or cfg.get("step2_wait_sec") or 2.0)
    deadline = time.time() + wait
    while time.time() < deadline:
        regions, _ = resolve_fast(cfg, step_hint=2)
        if regions and detect_step(regions.step2_prompt, regions.step1_prompt, regions.search) == 2:
            _log(actions, "[第2步] 界面已出现", on_progress)
            return regions
        time.sleep(0.2)
    return None


def _pick_step2_fast(
    cfg: dict,
    regions: CaptchaRegions,
    *,
    actions: list[str],
    on_progress: Callable[[str], None] | None,
) -> bool:
    fresh, loc = resolve_fast(cfg, step_hint=2)
    if fresh:
        regions = fresh
        _log(actions, loc, on_progress)

    area = regions.ball if regions.ball else regions.grid
    lib_hit = find_slow_ball_fast(area)
    bg = bool(cfg.get("background_click", True))

    if lib_hit:
        x, y, score, method = lib_hit
        _log(actions, f"[第2步] {method} → ({x},{y}) score={score:.2f}", on_progress)
        click_screen(x, y, background=bg)
        time.sleep(0.25)
        if click_confirm_button(cfg, regions.search):
            return True

    frames = int(cfg.get("fast_ball_frames") or 8)
    interval = int(cfg.get("fast_ball_interval_ms") or 70)
    candidates, hit = find_slowest_in_areas([area, regions.grid], frames=frames, interval_ms=interval, top_n=2)
    if not candidates:
        _log(actions, "[第2步] 未检测到动球", on_progress)
        return False

    for i, c in enumerate(candidates):
        click_screen(c.click_x, c.click_y, background=bg if i == 0 else False)
        time.sleep(0.28)
        if detect_step2_selected_from_region(hit or area) and click_confirm_button(cfg, regions.search):
            _log(actions, f"[第2步] 动球追踪 → ({c.click_x},{c.click_y})", on_progress)
            return True
    return click_confirm_button(cfg, regions.search)


def run_fast_agent(
    cfg: dict,
    *,
    keyword_override: str = "",
    on_progress: Callable[[str], None] | None = None,
) -> FastResult:
    """词库极速：预加载案例 → 快找窗 → 关键词匹配 → 过验证。"""
    actions: list[str] = []
    load_library_cache()
    stats = library_stats()
    _log(actions, f"词库就绪：第1步 {stats['step1_images']} 张 / {stats['step1_keywords']} 词，第2步慢球 {stats['step2_slow_images']} 张", on_progress)

    if not stats["ready"]:
        return FastResult(False, "第1步词库为空，请先收录几张正确图", actions=actions)

    regions, loc = resolve_fast(cfg)
    if not regions:
        return FastResult(False, loc, actions=actions)
    _log(actions, loc, on_progress)

    step = detect_step(regions.step1_prompt, regions.step2_prompt, regions.search)
    if step == 0:
        step = 1

    if step == 1:
        ok, msg = _pick_step1_fast(cfg, regions, keyword_override=keyword_override, actions=actions, on_progress=on_progress)
        if not ok:
            return FastResult(False, msg, step=1, actions=actions)
        _log(actions, "[第1步] 完成", on_progress)
        regions = _wait_step2_fast(cfg, actions, on_progress)
        if not regions:
            return FastResult(False, "第1步后未出现第2步", step=1, actions=actions)

    if not _pick_step2_fast(cfg, regions, actions=actions, on_progress=on_progress):
        return FastResult(False, "第2步失败", step=2, actions=actions)

    _log(actions, "[完成] 验证已通过 ✓", on_progress)
    return FastResult(True, "验证已通过（词库极速）", step=2, actions=actions)
