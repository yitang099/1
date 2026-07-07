"""词库极速：每次重新找窗 + 校验识别框 + 只点一次。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from slider_solver.screen_match import grab_region, save_region_image
from verify_auto.ball_slowest import find_slowest_moving_ball
from verify_auto.captcha_detect import auto_detect_regions
from verify_auto.click_util import click_screen
from verify_auto.confirm_click import click_confirm_smart
from verify_auto.library_cache import library_stats, load_library_cache, match_step1_best
from verify_auto.locate_cache import invalidate_cache, put_cache
from verify_auto.region_resolve import CaptchaRegions, ResolveResult, _fixed_regions, _resolve_auto
from verify_auto.region_validate import validate_regions
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


def _save_debug(regions: CaptchaRegions, tag: str, cfg: dict) -> None:
    try:
        d = Path(cfg.get("debug_dir") or "debug")
        d.mkdir(parents=True, exist_ok=True)
        save_region_image(regions.search, d / f"{tag}_search.png")
        save_region_image(regions.grid, d / f"{tag}_grid.png")
    except Exception:
        pass


def resolve_fresh(cfg: dict, *, step_hint: int = 0) -> tuple[CaptchaRegions | None, str]:
    """每次 F9 重新找窗，不用旧缓存（验证码随机位置）。"""
    invalidate_cache()

    if cfg.get("layout_profile"):
        auto = _resolve_auto(cfg, step_hint=step_hint)
        if auto:
            ok, msg = validate_regions(auto, step_hint=step_hint)
            if ok:
                _cache(auto, "layout")
                return auto, f"[布局] {msg}"

    fixed = _fixed_regions(cfg)
    if fixed:
        ok, msg = validate_regions(fixed, step_hint=step_hint)
        if ok:
            _cache(fixed, "fixed")
            return fixed, f"[框选] {msg}"

    for hint in (step_hint, 2, 1):
        auto = auto_detect_regions(step_hint=hint or 1)
        if not auto:
            continue
        ok, msg = validate_regions(auto, step_hint=hint or step_hint)
        if ok:
            _cache(auto, "auto")
            return auto, f"[找窗] {msg} @({auto.grid.left},{auto.grid.top} {auto.grid.width}x{auto.grid.height})"

    auto = auto_detect_regions(step_hint=step_hint or 1)
    if auto:
        _cache(auto, "auto")
        return auto, f"[找窗-未校验] ({auto.grid.left},{auto.grid.top})"
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
    g = regions.grid
    _log(actions, f"[第1步] 网格区 ({g.left},{g.top}) {g.width}x{g.height}", on_progress)
    cells = split_grid(grab_region(g))
    kw = _keyword(regions, keyword_override)

    if not kw:
        return False, "未读到关键词：请在参数栏填写（如 柠檬）"

    _log(actions, f"[第1步] 关键词「{kw}」词库匹配…", on_progress)
    hit = match_step1_best(cells, keyword=kw, min_score=min_score)
    if not hit:
        return False, f"词库「{kw}」未匹配（<{min_score:.2f}）。请补图或检查识别框是否对准网格"

    cell_i, score, lib_kw, ref = hit
    cx, cy = cell_centers(g)[cell_i]
    _log(actions, f"[第1步] 点击第{cell_i + 1}格 ({cx},{cy}) score={score:.2f}", on_progress)

    bg = bool(cfg.get("background_click", True))
    click_screen(cx, cy, background=bg)
    time.sleep(0.18)
    dialog = regions.search
    if not click_confirm_smart(cfg, regions.search, dialog):
        return False, "未点到确定（请框选蓝色确定按钮）"
    return True, lib_kw


def _wait_step2(cfg: dict, actions: list[str], on_progress: Callable[[str], None] | None) -> CaptchaRegions | None:
    deadline = time.time() + float(cfg.get("fast_step2_wait") or 2.0)
    while time.time() < deadline:
        regions, loc = resolve_fresh(cfg, step_hint=2)
        if regions and detect_step(regions.step2_prompt, regions.step1_prompt, regions.search) == 2:
            _log(actions, loc, on_progress)
            return regions
        time.sleep(0.18)
    return None


def _pick_step2(
    cfg: dict,
    regions: CaptchaRegions,
    *,
    actions: list[str],
    on_progress: Callable[[str], None] | None,
) -> bool:
    regions, loc = resolve_fresh(cfg, step_hint=2)
    _log(actions, loc, on_progress)
    area = regions.ball or regions.grid
    _log(actions, f"[第2步] 球区 ({area.left},{area.top}) {area.width}x{area.height}", on_progress)
    bg = bool(cfg.get("background_click", True))
    dialog = regions.search

    lib = find_slow_ball_fast(area, min_score=0.52)
    if lib:
        x, y, score, method = lib
        _log(actions, f"[第2步] {method} 点击 ({x},{y}) score={score:.2f}", on_progress)
        click_screen(x, y, background=bg)
        time.sleep(0.18)
        if click_confirm_smart(cfg, regions.search, dialog):
            return True
        _log(actions, "[第2步] 词库点中但确定失败", on_progress)
        return False

    _log(actions, "[第2步] 词库未中 → 6帧追踪", on_progress)
    r = find_slowest_moving_ball(
        area,
        frames=int(cfg.get("fast_ball_frames") or 6),
        interval_ms=int(cfg.get("fast_ball_interval_ms") or 60),
    )
    if not r.ok:
        return False
    _log(actions, f"[第2步] 追踪点击 ({r.click_x},{r.click_y})", on_progress)
    click_screen(r.click_x, r.click_y, background=bg)
    time.sleep(0.18)
    return click_confirm_smart(cfg, regions.search, dialog)


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
        f"词库 {stats['step1_images']} 张/{stats['step1_keywords']} 词 | 慢球 {stats['step2_slow_images']} 张",
        on_progress,
    )
    if not stats["ready"]:
        return FastResult(False, "第1步词库为空，请先收录图片", actions=actions)

    regions, loc = resolve_fresh(cfg, step_hint=0)
    if not regions:
        return FastResult(False, loc, actions=actions)
    _log(actions, loc, on_progress)
    _save_debug(regions, "run", cfg)

    step = detect_step(regions.step1_prompt, regions.step2_prompt, regions.search)
    _log(actions, f"当前步骤={step or '?'}", on_progress)

    if step == 1:
        ok, msg = _pick_step1(cfg, regions, keyword_override=keyword_override, actions=actions, on_progress=on_progress)
        if not ok:
            return FastResult(False, msg, step=1, actions=actions)
        regions = _wait_step2(cfg, actions, on_progress)
        if not regions:
            return FastResult(False, "第1步后未出现第2步", step=1, actions=actions)
    elif step != 2:
        return FastResult(False, "未识别第1步或第2步，识别框可能偏移。请点「测试自动定位」检查", actions=actions)

    if not _pick_step2(cfg, regions, actions=actions, on_progress=on_progress):
        return FastResult(False, "第2步失败（检查球区域是否框在动球区）", step=2, actions=actions)

    _log(actions, "[完成] ✓", on_progress)
    return FastResult(True, "验证已通过", step=2, actions=actions)
