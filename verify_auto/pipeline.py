"""一键：第1步选图 → 确定 → 等第2步 → 最慢球 → 确定。"""
from __future__ import annotations

import time
from dataclasses import dataclass

from verify_auto.click_util import click_screen

from slider_solver.screen_match import Region, find_on_screen
from verify_auto.ball_slowest import find_slowest_moving_ball
from verify_auto.config import load_config
from verify_auto.region_resolve import resolve_regions
from verify_auto.screen_detect import detect_step
from verify_auto.selection_marker import detect_step1_selected_from_region, detect_step2_selected_from_region
from verify_auto.step1_library import run_step1_library
from verify_auto.step1_pick import run_step1


@dataclass
class PipelineResult:
    ok: bool
    message: str


def _click_confirm(cfg: dict, search: Region | None = None) -> bool:
    tpl = cfg.get("confirm_template") or ""
    if not tpl:
        return False
    m = find_on_screen(tpl, search, threshold=0.55)
    if not m:
        return False
    import cv2

    img = cv2.imdecode(np.fromfile(tpl, dtype=np.uint8), cv2.IMREAD_COLOR)
    cx = m.screen_x + img.shape[1] // 2
    cy = m.screen_y + img.shape[0] // 2
    bg = bool(cfg.get("background_click", True))
    return click_screen(cx, cy, background=bg).ok


def run_full_pipeline(cfg: dict | None = None, *, keyword_override: str = "") -> PipelineResult:
    cfg = cfg or load_config()
    resolved = resolve_regions(cfg, step_hint=0)
    if not resolved.ok or not resolved.regions:
        return PipelineResult(False, resolved.message)

    areas = resolved.regions
    prompt, grid, ball = areas.prompt, areas.grid, areas.ball
    locate_note = resolved.message

    step = detect_step(prompt)
    if step == 2:
        r2 = resolve_regions(cfg, step_hint=2)
        if r2.ok and r2.regions:
            areas = r2.regions
            locate_note = r2.message
        return _run_step2_only(cfg, areas.ball, areas.search, locate_note)

    if cfg.get("use_library", True):
        r1 = run_step1_library(
            prompt,
            grid,
            keyword_override=keyword_override,
            min_score=float(cfg.get("step1_min_score") or 0.72),
        )
        if not r1.ok and keyword_override:
            r1 = run_step1_library(prompt, grid, keyword_override=keyword_override, min_score=0.65)
    else:
        r1 = None

    if r1 is None or (not r1.ok and cfg.get("use_library", True)):
        r1_ai = run_step1(prompt, grid, keyword_override=keyword_override, debug_dir=cfg.get("debug_dir"))
        if not r1_ai.ok:
            msg = r1.message if r1 and not r1.ok else r1_ai.message
            return PipelineResult(False, f"{locate_note} | {msg}")
        r1 = r1_ai
    elif not r1.ok:
        return PipelineResult(False, f"{locate_note} | {r1.message}")

    bg = bool(cfg.get("background_click", True))
    click_screen(r1.click_x, r1.click_y, background=bg)
    time.sleep(0.35)
    marker = detect_step1_selected_from_region(grid)
    if marker and marker[0] != r1.cell_index:
        return PipelineResult(
            False,
            f"第1步点击后勾出现在第 {marker[0] + 1} 格，与预期第 {r1.cell_index + 1} 格不符",
        )
    if not _click_confirm(cfg, areas.search):
        return PipelineResult(False, f"第1步已点图 {r1.cell_index + 1}，但未在小窗内找到确定按钮")

    wait_sec = float(cfg.get("step2_wait_sec") or 2.5)
    deadline = time.time() + wait_sec
    while time.time() < deadline:
        r2 = resolve_regions(cfg, step_hint=2)
        if r2.ok and r2.regions and detect_step(r2.regions.prompt) == 2:
            areas = r2.regions
            ball = areas.ball
            break
        time.sleep(0.3)
    else:
        return PipelineResult(False, "第1步完成，但未等到第2步界面（可调 step2_wait_sec）")

    r2 = _run_step2_only(cfg, ball, areas.search, locate_note)
    if not r2.ok:
        return PipelineResult(False, f"第1步 OK；{r2.message}")
    return PipelineResult(True, f"{locate_note} | 全流程完成。{r1.message} | {r2.message}")


def _run_step2_only(
    cfg: dict,
    ball: Region,
    search: Region | None = None,
    locate_note: str = "",
) -> PipelineResult:
    r = find_slowest_moving_ball(
        ball,
        frames=int(cfg.get("ball_frames") or 15),
        interval_ms=int(cfg.get("ball_interval_ms") or 100),
    )
    if not r.ok:
        prefix = f"{locate_note} | " if locate_note else ""
        return PipelineResult(False, f"{prefix}{r.message}")
    bg = bool(cfg.get("background_click", True))
    click_screen(r.click_x, r.click_y, background=bg)
    time.sleep(0.4)
    marker = detect_step2_selected_from_region(ball)
    if marker:
        lx, ly, _ = marker
        dist = ((ball.left + lx - r.click_x) ** 2 + (ball.top + ly - r.click_y) ** 2) ** 0.5
        if dist > 45:
            return PipelineResult(False, f"第2步点击后蓝色圈位置与点击点相差 {dist:.0f}px")
    if not _click_confirm(cfg, search):
        return PipelineResult(False, f"已点最慢球，未在小窗内找到确定：{r.message}")
    prefix = f"{locate_note} | " if locate_note else ""
    return PipelineResult(True, f"{prefix}{r.message}")
