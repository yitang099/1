"""内置 AI 代理：自动找窗 → 第1步选图 → 第2步点最慢球 → 过验证。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from slider_solver.screen_match import grab_region
from verify_auto.ball_slowest import find_slowest_in_areas
from verify_auto.captcha_detect import auto_detect_regions_robust
from verify_auto.click_util import click_screen
from verify_auto.confirm_click import click_confirm_button
from verify_auto.locate_cache import put_cache
from verify_auto.region_resolve import CaptchaRegions, ResolveResult, _fixed_regions, _resolve_auto
from verify_auto.screen_detect import _detect_from_region
from verify_auto.selection_marker import (
    detect_step1_selected_from_region,
    detect_step2_selected_from_region,
)
from verify_auto.step1_keyword import extract_keyword_robust
from verify_auto.step1_pick import cell_centers, extract_keyword, split_grid


@dataclass
class AgentResult:
    ok: bool
    message: str
    step: int = 0
    actions: list[str] = field(default_factory=list)


def _log(actions: list[str], msg: str, on_progress: Callable[[str], None] | None) -> None:
    if not msg:
        return
    actions.append(msg)
    if on_progress:
        on_progress(msg)


def _cache_regions(regions: CaptchaRegions, message: str) -> None:
    put_cache(ResolveResult(True, message, regions))


def _resolve_regions(cfg: dict, step_hint: int, *, strong: bool) -> tuple[CaptchaRegions | None, str]:
    """多策略找窗：布局档案 → 视觉推断 → 固定坐标。"""
    use_strong = strong or cfg.get("ai_strong_mode", True)
    no_cal = bool(cfg.get("ai_auto_no_calibrate", True))

    if cfg.get("layout_profile"):
        hit = _resolve_auto(cfg, step_hint=step_hint)
        if hit:
            _cache_regions(hit, "layout")
            return hit, f"[布局定位] ({hit.step1_prompt.left},{hit.step1_prompt.top})"

    if use_strong:
        auto = auto_detect_regions_robust(step_hint=step_hint)
        if auto:
            _cache_regions(auto, "auto")
            return auto, f"[自动找窗] ({auto.step1_prompt.left},{auto.step1_prompt.top})"

    fixed = _fixed_regions(cfg)
    if fixed and not (no_cal and use_strong):
        return fixed, "[已框选区域]"
    if fixed:
        return fixed, "[已框选区域]"

    auto = auto_detect_regions_robust(step_hint=step_hint)
    if auto:
        _cache_regions(auto, "auto")
        return auto, f"[自动找窗] ({auto.step1_prompt.left},{auto.step1_prompt.top})"
    return None, "未找到验证小窗，请先弹出验证码"


def _perceive(regions: CaptchaRegions) -> tuple[int, str]:
    for region in (regions.search, regions.step2_prompt, regions.step1_prompt):
        step, text = _detect_from_region(region)
        if step:
            return step, text
    return 0, ""


def _keyword_from_regions(regions: CaptchaRegions, override: str) -> tuple[str, str]:
    if override:
        return override.strip(), ""
    kw, debug = extract_keyword_robust(
        step1_prompt=regions.step1_prompt,
        search=regions.search,
        grid=regions.grid,
    )
    return kw, debug


def _click_confirm_retry(cfg: dict, search, times: int = 3) -> bool:
    for _ in range(times):
        if click_confirm_button(cfg, search):
            return True
        time.sleep(0.15)
    return False


def _try_step1_click(
    cfg: dict,
    regions: CaptchaRegions,
    *,
    cx: int,
    cy: int,
    cell_no: int,
    label: str,
    actions: list[str],
    on_progress: Callable[[str], None] | None,
) -> bool:
    _log(actions, label, on_progress)
    bg = bool(cfg.get("background_click", True))
    click_screen(cx, cy, background=bg)
    time.sleep(0.35)
    marker = detect_step1_selected_from_region(regions.grid)
    if not marker:
        click_screen(cx, cy, background=False)
        time.sleep(0.3)
        marker = detect_step1_selected_from_region(regions.grid)
    if marker:
        _log(actions, f"[第1步] 第{cell_no}格已选中 ✓", on_progress)
    return _click_confirm_retry(cfg, regions.search)


def _pick_step1(
    cfg: dict,
    regions: CaptchaRegions,
    *,
    keyword_override: str,
    actions: list[str],
    on_progress: Callable[[str], None] | None,
    attempt: int,
) -> tuple[bool, str]:
    kw, ocr_debug = _keyword_from_regions(regions, keyword_override)
    if ocr_debug:
        _log(actions, f"[第1步] OCR: {ocr_debug!r}", on_progress)
    if not kw:
        _log(actions, "[第1步] 未读到关键词，将尝试全词库匹配 / 逐格试探", on_progress)

    if kw:
        _log(actions, f"[第1步] 关键词「{kw}」", on_progress)

    min_score = float(cfg.get("step1_min_score") or 0.72) - attempt * 0.06
    grid_img = grab_region(regions.grid)
    cells = split_grid(grid_img)
    centers = cell_centers(regions.grid)
    tried: set[int] = set()

    def _try_cell(cell_i: int, cx: int, cy: int, label: str) -> bool:
        if cell_i in tried:
            return False
        tried.add(cell_i)
        return _try_step1_click(
            cfg, regions, cx=cx, cy=cy, cell_no=cell_i + 1,
            label=label, actions=actions, on_progress=on_progress,
        )

    # 1) 全词库扫描（不依赖 OCR 关键词）
    if cfg.get("use_library", True):
        from verify_auto.library_store import rank_cells_global_library

        global_hits = rank_cells_global_library(cells, min_score=max(0.50, min_score - 0.12), top_n=4)
        for cell_i, score, lib_kw, ref in global_hits:
            cx, cy = centers[cell_i]
            label = f"[第1步] 全库匹配「{lib_kw}」→ 第{cell_i + 1}格 ({score:.2f}) ref={ref}"
            if _try_cell(cell_i, cx, cy, label):
                return True, lib_kw or kw

    # 2) 指定关键词词库
    if kw and cfg.get("use_library", True):
        from verify_auto.step1_library import list_step1_library_candidates

        _, candidates = list_step1_library_candidates(
            regions.step1_prompt,
            regions.grid,
            keyword_override=kw,
            min_score=max(0.50, min_score - 0.10),
            top_n=3,
        )
        for i, (cell_i, score, ref, cx, cy) in enumerate(candidates):
            label = f"[第1步] 词库候选{i + 1} → 第{cell_i + 1}格 ({score:.2f}) ref={ref}"
            if _try_cell(cell_i, cx, cy, label):
                return True, kw

    # 3) 本地颜色/物体启发式
    if kw:
        from verify_auto.step1_local import rank_cells_local

        for cell_i, score in rank_cells_local(kw, cells, top_n=3):
            cx, cy = centers[cell_i]
            label = f"[第1步] 本地识图 → 第{cell_i + 1}格 ({score:.2f})"
            if _try_cell(cell_i, cx, cy, label):
                return True, kw

    # 4) 视觉 API
    api_key = (cfg.get("ai_api_key") or "").strip()
    if api_key and kw and (cfg.get("ai_enabled", True) or cfg.get("ai_strong_mode", True)):
        from verify_auto.ai_vision import pick_step1_cell_via_api

        idx, msg = pick_step1_cell_via_api(grid_img, kw, cfg)
        _log(actions, f"[第1步] {msg}", on_progress)
        if idx is not None:
            cx, cy = centers[idx]
            if _try_cell(idx, cx, cy, f"[第1步] API → 第{idx + 1}格"):
                return True, kw

    # 5) 逐格试探：点确定后看是否进入第2步
    from verify_auto.step1_probe import probe_step1_cells

    _log(actions, "[第1步] 启动逐格试探（最多6格）", on_progress)

    def probe_log(msg: str) -> None:
        _log(actions, msg, on_progress)

    ok, cell_i = probe_step1_cells(cfg, regions, on_progress=probe_log, wait_sec=1.4 - attempt * 0.1)
    if ok:
        return True, kw or f"第{cell_i + 1}格"

    return False, "第1步全部策略失败（建议用「开始持续收录」存几张正确图到词库）"


def _wait_step2(cfg: dict, actions: list[str], on_progress: Callable[[str], None] | None) -> CaptchaRegions | None:
    wait = float(cfg.get("step2_wait_sec") or 4.0)
    deadline = time.time() + wait
    while time.time() < deadline:
        time.sleep(0.3)
        regions, _ = _resolve_regions(cfg, 2, strong=True)
        if regions and _perceive(regions)[0] == 2:
            _log(actions, "[第2步] 界面已出现", on_progress)
            return regions
    return None


def _pick_step2(
    cfg: dict,
    regions: CaptchaRegions,
    *,
    actions: list[str],
    on_progress: Callable[[str], None] | None,
    attempt: int,
) -> bool:
    fresh, loc = _resolve_regions(cfg, 2, strong=True)
    if fresh:
        regions = fresh
        _log(actions, f"[第2步] 重新定位 {loc}", on_progress)
    time.sleep(0.25 + attempt * 0.1)
    frames = int(cfg.get("ball_frames") or 14) + attempt * 2
    interval = max(60, int(cfg.get("ball_interval_ms") or 80) - attempt * 10)
    candidates, hit = find_slowest_in_areas(
        [regions.ball, regions.grid], frames=frames, interval_ms=interval, top_n=4
    )
    if not candidates or not hit:
        _log(actions, "[第2步] 未检测到动球", on_progress)
        return False

    bg = bool(cfg.get("background_click", True))
    for i, c in enumerate(candidates):
        click_screen(c.click_x, c.click_y, background=bg if i == 0 else False)
        time.sleep(0.4)
        marker = detect_step2_selected_from_region(hit)
        _log(actions, f"[第2步] 点候选{i + 1} ({c.click_x},{c.click_y}) {'✓' if marker else '…'}", on_progress)
        if marker and _click_confirm_retry(cfg, regions.search):
            return True
    return _click_confirm_retry(cfg, regions.search)


def _run_once(
    cfg: dict,
    *,
    keyword_override: str,
    actions: list[str],
    on_progress: Callable[[str], None] | None,
    attempt: int,
) -> AgentResult:
    regions, loc = _resolve_regions(cfg, 0, strong=True)
    if not regions:
        return AgentResult(False, loc, actions=actions)
    _log(actions, loc, on_progress)

    step, text = _perceive(regions)
    if step == 0:
        return AgentResult(False, f"未识别步骤: {text[:40]!r}", actions=actions)

    if step == 1:
        ok, msg = _pick_step1(
            cfg, regions, keyword_override=keyword_override,
            actions=actions, on_progress=on_progress, attempt=attempt,
        )
        if not ok:
            return AgentResult(False, msg, step=1, actions=actions)
        _log(actions, "[第1步] 完成 → 等第2步", on_progress)
        regions = _wait_step2(cfg, actions, on_progress)
        if not regions:
            return AgentResult(False, "第1步后未出现第2步", step=1, actions=actions)
        step = 2

    if step == 2:
        if not _pick_step2(cfg, regions, actions=actions, on_progress=on_progress, attempt=attempt):
            return AgentResult(False, "第2步失败", step=2, actions=actions)
        _log(actions, "[完成] 验证已通过 ✓", on_progress)
        return AgentResult(True, "验证已通过", step=2, actions=actions)

    return AgentResult(False, "未知状态", actions=actions)


def run_strong_agent(
    cfg: dict,
    *,
    keyword_override: str = "",
    on_progress: Callable[[str], None] | None = None,
    max_attempts: int = 3,
) -> AgentResult:
    """强化 AI：自动找窗 → 第1步选图 → 第2步点最慢球 → 过验证（失败自动重试）。"""
    actions: list[str] = []
    kw = keyword_override.strip()
    last = AgentResult(False, "未执行", actions=actions)

    for attempt in range(max_attempts):
        if attempt:
            _log(actions, f"--- 重试 {attempt + 1}/{max_attempts} ---", on_progress)
            time.sleep(0.6)
        last = _run_once(cfg, keyword_override=kw, actions=actions, on_progress=on_progress, attempt=attempt)
        if last.ok:
            return last

    return last


def run_ai_agent(
    cfg: dict,
    *,
    keyword_override: str = "",
    on_progress: Callable[[str], None] | None = None,
    max_rounds: int = 1,
) -> AgentResult:
    """兼容入口 → 强化代理。"""
    return run_strong_agent(
        cfg,
        keyword_override=keyword_override,
        on_progress=on_progress,
        max_attempts=max(1, max_rounds),
    )


def run_ai_learn_once(
    cfg: dict,
    regions: CaptchaRegions,
    *,
    keyword_override: str = "",
) -> tuple[int, str]:
    step, text = _perceive(regions)
    kw = keyword_override or extract_keyword(text) or extract_keyword_robust(
        step1_prompt=regions.step1_prompt, search=regions.search, grid=regions.grid
    )[0]
    return step, kw
