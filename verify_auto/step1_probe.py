"""第1步兜底：逐格点击+确定，检测是否进入第2步。"""
from __future__ import annotations

import time
from typing import Callable

from verify_auto.click_util import click_screen
from verify_auto.confirm_click import click_confirm_button
from verify_auto.region_resolve import CaptchaRegions
from verify_auto.screen_detect import detect_step
from verify_auto.step1_pick import cell_centers


def probe_step1_cells(
    cfg: dict,
    regions: CaptchaRegions,
    *,
    on_progress: Callable[[str], None] | None = None,
    wait_sec: float = 1.6,
) -> tuple[bool, int]:
    """
    依次点 6 格并确定，若界面切到第2步则成功。
    返回 (是否成功, 成功的格子序号 0-based，失败为 -1)。
    """
    centers = cell_centers(regions.grid)
    bg = bool(cfg.get("background_click", True))

    for i, (cx, cy) in enumerate(centers):
        if on_progress:
            on_progress(f"[第1步] 试探第{i + 1}格 ({cx},{cy})")
        click_screen(cx, cy, background=bg)
        time.sleep(0.3)
        click_screen(cx, cy, background=False)
        time.sleep(0.2)
        if not click_confirm_button(cfg, regions.search):
            time.sleep(0.15)
            click_confirm_button(cfg, regions.search)
        time.sleep(wait_sec)

        step = detect_step(regions.step1_prompt, regions.step2_prompt, regions.search)
        if step == 2:
            if on_progress:
                on_progress(f"[第1步] 试探成功 → 第{i + 1}格正确 ✓")
            return True, i
        if step == 0:
            # 小窗可能刷新，稍等再试下一格
            time.sleep(0.4)

    return False, -1
