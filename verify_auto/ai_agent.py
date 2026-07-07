"""内置 AI 代理：自己看屏幕 → 判断步骤 → 决定点哪里。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from slider_solver.screen_match import Region, grab_region
from verify_auto.ball_slowest import find_slowest_in_areas
from verify_auto.captcha_detect import auto_detect_regions
from verify_auto.click_util import click_screen
from verify_auto.confirm_click import click_confirm_button
from verify_auto.region_resolve import CaptchaRegions, _fixed_regions, resolve_regions
from verify_auto.screen_detect import _detect_from_region
from verify_auto.selection_marker import detect_step2_selected_from_region
from verify_auto.step1_library import run_step1_library
from verify_auto.step1_pick import cell_centers, extract_keyword, ocr_image


@dataclass
class AgentResult:
    ok: bool
    message: str
    step: int = 0
    actions: list[str] = field(default_factory=list)


def _log(actions: list[str], msg: str, on_progress: Callable[[str], None] | None) -> None:
    actions.append(msg)
    if on_progress:
        on_progress(msg)


def _resolve_regions(cfg: dict, step_hint: int) -> tuple[CaptchaRegions | None, str]:
    fixed = _fixed_regions(cfg)
    if fixed:
        return fixed, "使用已框选区域"
    auto = auto_detect_regions(step_hint=step_hint)
    if auto:
        return auto, f"AI 自动定位 @ ({auto.step1_prompt.left},{auto.step1_prompt.top})"
    r = resolve_regions(cfg, step_hint=step_hint, force_refresh=True)
    if r.ok and r.regions:
        return r.regions, r.message
    return None, r.message if r else "未找到验证窗"


def _perceive(regions: CaptchaRegions) -> tuple[int, str]:
    for region in (regions.step2_prompt, regions.step1_prompt):
        step, text = _detect_from_region(region)
        if step:
            return step, text
    return 0, ""


def _pick_step1(
    cfg: dict,
    regions: CaptchaRegions,
    *,
    keyword_override: str,
    actions: list[str],
    on_progress: Callable[[str], None] | None,
) -> tuple[bool, str]:
    prompt_img = grab_region(regions.step1_prompt)
    grid_img = grab_region(regions.grid)
    kw = keyword_override or extract_keyword(ocr_image(prompt_img))
    if not kw:
        return False, "未读到关键词"

    _log(actions, f"[AI] 第1步关键词「{kw}」", on_progress)

    if cfg.get("use_library", True):
        r = run_step1_library(
            regions.step1_prompt,
            regions.grid,
            keyword_override=kw,
            min_score=float(cfg.get("step1_min_score") or 0.72),
        )
        if r.ok:
            _log(actions, f"[AI] 词库匹配 → 第{r.cell_index + 1}格", on_progress)
            bg = bool(cfg.get("background_click", True))
            click_screen(r.click_x, r.click_y, background=bg)
            time.sleep(0.3)
            if click_confirm_button(cfg, regions.search):
                return True, kw
            return False, "未点到确定"

    if cfg.get("ai_enabled") and (cfg.get("ai_api_key") or "").strip():
        from verify_auto.ai_vision import pick_step1_cell_via_api

        idx, msg = pick_step1_cell_via_api(grid_img, kw, cfg)
        _log(actions, f"[AI] {msg}", on_progress)
        if idx is not None:
            centers = cell_centers(regions.grid)
            cx, cy = centers[idx]
            bg = bool(cfg.get("background_click", True))
            click_screen(cx, cy, background=bg)
            time.sleep(0.3)
            if click_confirm_button(cfg, regions.search):
                return True, kw
            return False, "未点到确定"

    from verify_auto.step1_pick import run_step1

    r = run_step1(regions.step1_prompt, regions.grid, keyword_override=kw)
    if not r.ok:
        return False, r.message
    _log(actions, r.message, on_progress)
    bg = bool(cfg.get("background_click", True))
    click_screen(r.click_x, r.click_y, background=bg)
    time.sleep(0.3)
    if not click_confirm_button(cfg, regions.search):
        return False, "未点到确定"
    return True, kw


def _pick_step2(
    cfg: dict,
    regions: CaptchaRegions,
    *,
    actions: list[str],
    on_progress: Callable[[str], None] | None,
) -> bool:
    time.sleep(0.2)
    frames = int(cfg.get("ball_frames") or 12)
    interval = int(cfg.get("ball_interval_ms") or 80)
    candidates, hit = find_slowest_in_areas([regions.ball, regions.grid], frames=frames, interval_ms=interval, top_n=3)
    if not candidates or not hit:
        _log(actions, "[AI] 第2步未检测到动球", on_progress)
        return False

    bg = bool(cfg.get("background_click", True))
    for i, c in enumerate(candidates):
        click_screen(c.click_x, c.click_y, background=bg if i == 0 else False)
        time.sleep(0.35)
        marker = detect_step2_selected_from_region(hit)
        _log(actions, f"[AI] 第2步点击 ({c.click_x},{c.click_y}) {'✓' if marker else '×'}", on_progress)
        if marker:
            return click_confirm_button(cfg, regions.search)
    return click_confirm_button(cfg, regions.search)


def run_ai_agent(
    cfg: dict,
    *,
    keyword_override: str = "",
    on_progress: Callable[[str], None] | None = None,
    max_rounds: int = 3,
) -> AgentResult:
    """AI 代理：自动找窗 → 判断步骤 → 执行全流程（可连过多次验证）。"""
    actions: list[str] = []
    kw_override = keyword_override.strip()
    rounds = 0

    while rounds < max_rounds:
        regions, loc_msg = _resolve_regions(cfg, step_hint=0)
        if not regions:
            return AgentResult(False, loc_msg, actions=actions)
        _log(actions, loc_msg, on_progress)

        step, text = _perceive(regions)
        if step == 0:
            return AgentResult(False, f"未识别步骤 OCR={text[:30]!r}", actions=actions)

        if step == 1:
            ok, msg = _pick_step1(cfg, regions, keyword_override=kw_override, actions=actions, on_progress=on_progress)
            if not ok:
                return AgentResult(False, msg, step=1, actions=actions)
            _log(actions, "[AI] 第1步完成，等待第2步…", on_progress)
            deadline = time.time() + float(cfg.get("step2_wait_sec") or 3.0)
            while time.time() < deadline:
                time.sleep(0.35)
                regions, _ = _resolve_regions(cfg, step_hint=2)
                if regions and _perceive(regions)[0] == 2:
                    break
            else:
                return AgentResult(False, "第1步后未出现第2步", step=1, actions=actions)
            step = 2

        if step == 2:
            regions, _ = _resolve_regions(cfg, step_hint=2)
            if not regions:
                return AgentResult(False, "第2步定位失败", step=2, actions=actions)
            if not _pick_step2(cfg, regions, actions=actions, on_progress=on_progress):
                return AgentResult(False, "第2步失败", step=2, actions=actions)
            _log(actions, "[AI] 第2步完成 ✓", on_progress)
            rounds += 1
            time.sleep(0.8)
            continue

    return AgentResult(True, f"AI 代理完成 {rounds} 轮", actions=actions)


def run_ai_learn_once(
    cfg: dict,
    regions: CaptchaRegions,
    *,
    keyword_override: str = "",
) -> tuple[int, str]:
    """收录时 AI 判断当前该做什么，返回 (step, keyword)。"""
    step, text = _perceive(regions)
    kw = keyword_override or extract_keyword(text) or extract_keyword(ocr_image(grab_region(regions.step1_prompt)))
    return step, kw
