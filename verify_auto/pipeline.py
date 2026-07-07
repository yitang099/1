"""一键：第1步选图 → 确定 → 等第2步 → 最慢球 → 确定。"""
from __future__ import annotations

import time
from dataclasses import dataclass

import pyautogui

from slider_solver.screen_match import Region, find_on_screen
from verify_auto.ball_slowest import find_slowest_moving_ball
from verify_auto.config import load_config
from verify_auto.screen_detect import detect_step
from verify_auto.selection_marker import detect_step1_selected_from_region, detect_step2_selected_from_region
from verify_auto.step1_library import run_step1_library
from verify_auto.step1_pick import run_step1


@dataclass
class PipelineResult:
    ok: bool
    message: str


def _click_confirm(cfg: dict) -> bool:
    tpl = cfg.get("confirm_template") or ""
    if not tpl:
        return False
    m = find_on_screen(tpl, None, threshold=0.55)
    if not m:
        return False
    import cv2
    import numpy as np

    img = cv2.imdecode(np.fromfile(tpl, dtype=np.uint8), cv2.IMREAD_COLOR)
    cx = m.screen_x + img.shape[1] // 2
    cy = m.screen_y + img.shape[0] // 2
    pyautogui.click(cx, cy)
    return True


def run_full_pipeline(cfg: dict | None = None, *, keyword_override: str = "") -> PipelineResult:
    cfg = cfg or load_config()
    prompt = Region.from_dict(cfg.get("prompt_region"))
    grid = Region.from_dict(cfg.get("grid_region"))
    ball = Region.from_dict(cfg.get("step2_ball_region"))

    if not prompt or not grid:
        return PipelineResult(False, "请先框选：提示文字区 + 图片网格区")

    step = detect_step(prompt)
    if step == 2 or step == 0:
        # 若已在第2步，只做球
        if ball and step == 2:
            return _run_step2_only(cfg, ball)

    # 第1步：优先词库文件夹匹配
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
            return PipelineResult(False, msg)
        r1 = r1_ai
    elif not r1.ok:
        return PipelineResult(False, r1.message)

    pyautogui.click(r1.click_x, r1.click_y)
    time.sleep(0.35)
    marker = detect_step1_selected_from_region(grid)
    if marker and marker[0] != r1.cell_index:
        return PipelineResult(
            False,
            f"第1步点击后勾出现在第 {marker[0] + 1} 格，与预期第 {r1.cell_index + 1} 格不符",
        )
    if not _click_confirm(cfg):
        return PipelineResult(False, f"第1步已点图 {r1.cell_index + 1}，但未找到确定按钮")

    # 等第2步出现
    wait_sec = float(cfg.get("step2_wait_sec") or 2.5)
    deadline = time.time() + wait_sec
    while time.time() < deadline:
        if detect_step(prompt) == 2:
            break
        time.sleep(0.3)
    else:
        return PipelineResult(False, "第1步完成，但未等到第2步界面（可调 step2_wait_sec）")

    if not ball:
        return PipelineResult(False, "第1步已过，请框选第2步球区域后再跑")

    r2 = _run_step2_only(cfg, ball)
    if not r2.ok:
        return PipelineResult(False, f"第1步 OK；{r2.message}")
    return PipelineResult(True, f"全流程完成。{r1.message} | {r2.message}")


def _run_step2_only(cfg: dict, ball: Region) -> PipelineResult:
    r = find_slowest_moving_ball(
        ball,
        frames=int(cfg.get("ball_frames") or 15),
        interval_ms=int(cfg.get("ball_interval_ms") or 100),
    )
    if not r.ok:
        return PipelineResult(False, r.message)
    pyautogui.click(r.click_x, r.click_y)
    time.sleep(0.4)
    marker = detect_step2_selected_from_region(ball)
    if marker:
        lx, ly, _ = marker
        dist = ((ball.left + lx - r.click_x) ** 2 + (ball.top + ly - r.click_y) ** 2) ** 0.5
        if dist > 45:
            return PipelineResult(False, f"第2步点击后蓝色圈位置与点击点相差 {dist:.0f}px")
    if not _click_confirm(cfg):
        return PipelineResult(False, f"已点最慢球，未找到确定：{r.message}")
    return PipelineResult(True, r.message)
