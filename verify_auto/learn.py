"""手动学习：把当前屏收录进词库文件夹。"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from slider_solver.screen_match import Region, grab_region
from verify_auto.library_store import save_step1_image, save_step2_ball_crop, save_step2_scene
from verify_auto.selection_marker import (
    detect_step1_selected_from_region,
    wait_for_step1_marker,
    wait_for_step2_marker,
)
from verify_auto.step1_pick import cell_index_at_point, extract_keyword, ocr_image, split_grid


@dataclass
class LearnResult:
    ok: bool
    message: str
    path: str = ""
    step1_count: int = 0
    step2_count: int = 0


LEARN_POLL_SEC = 0.12
STEP2_FAST_FRAMES = 3
STEP2_FAST_INTERVAL_MS = 50
LOCATE_REFRESH_SEC = 12.0
STEP1_MARKER_THRESHOLD = 0.22


@dataclass
class _LearnCtx:
    step: int = 0
    regions: Any = None
    pending_cell: int | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


def _collect_step2_with_click(
    cfg: dict,
    regions: Any,
    *,
    on_progress: Callable[[str], None] | None = None,
    frames: int = STEP2_FAST_FRAMES,
    interval_ms: int = STEP2_FAST_INTERVAL_MS,
) -> bool:
    """快速分析最慢球 → 自动点击 → 收录截图。"""
    from verify_auto.ball_slowest import find_slowest_moving_ball
    from verify_auto.click_util import click_screen
    from verify_auto.selection_marker import detect_step2_selected_from_region

    r = find_slowest_moving_ball(regions.ball, frames=frames, interval_ms=interval_ms)
    if not r.ok:
        if on_progress:
            on_progress(f"[第2步] 动球分析失败: {r.message}")
        return False

    bg = bool(cfg.get("background_click", True))
    click_screen(r.click_x, r.click_y, background=bg)
    time.sleep(0.25)

    lx = r.click_x - regions.ball.left
    ly = r.click_y - regions.ball.top
    _save_ball_crop_at(
        regions.ball,
        lx,
        ly,
        {
            "source": "auto_motion_click",
            "screen_x": r.click_x,
            "screen_y": r.click_y,
            "move": r.message,
        },
    )

    marker = detect_step2_selected_from_region(regions.ball)
    msg = f"[第2步] 已点击最慢球 ({r.click_x},{r.click_y})"
    if marker:
        msg += " → 出现选中圈 ✓"
    else:
        msg += " → 请看是否点对"
    if on_progress:
        on_progress(msg)
    return True


def _save_step1_cell(
    regions: Any,
    cell_index: int,
    kw: str,
    *,
    source: str,
    conf: float = 0.0,
) -> None:
    cells = split_grid(grab_region(regions.grid))
    save_step1_image(kw, cells[cell_index])


def _try_save_step1(
    ctx: _LearnCtx,
    *,
    cell_index: int,
    kw_override: str,
    saved_step1: set[str],
    round_id: int,
    on_progress: Callable[[str], None] | None,
) -> tuple[bool, int]:
    """尝试收录第1步，返回 (是否新收录, cell_index)。"""
    with ctx.lock:
        regions = ctx.regions
    if not regions:
        return False, cell_index

    prompt_img = grab_region(regions.prompt)
    kw = kw_override or extract_keyword(ocr_image(prompt_img))
    if not kw:
        if on_progress:
            on_progress("[第1步] 未读到关键词，请在参数里填写或等提示字清晰")
        return False, cell_index

    sig = f"{round_id}:{kw}#{cell_index}"
    if sig in saved_step1:
        return False, cell_index

    _save_step1_cell(regions, cell_index, kw, source="learn", conf=0.0)
    saved_step1.add(sig)
    if on_progress:
        on_progress(f"[第1步] 「{kw}」第{cell_index + 1}格 已收录 (本轮{round_id + 1})")
    return True, cell_index


def _start_grid_listener(ctx: _LearnCtx, stop_event: threading.Event):
    from pynput import mouse

    def on_click(x, y, button, pressed):
        if not pressed or button != mouse.Button.left:
            return
        if stop_event.is_set():
            return False
        with ctx.lock:
            if ctx.step != 1 or not ctx.regions:
                return
            g = ctx.regions.grid
            if not (g.left <= x < g.left + g.width and g.top <= y < g.top + g.height):
                return
            cell = cell_index_at_point(g, int(x), int(y))
            if cell >= 0:
                ctx.pending_cell = cell

    listener = mouse.Listener(on_click=on_click)
    listener.start()
    return listener


def learn_watch_loop(
    cfg: dict,
    stop_event: threading.Event,
    *,
    keyword_override: str = "",
    on_progress: Callable[[str], None] | None = None,
) -> LearnResult:
    """持续收录：提示字驱动状态机 + 点击网格/蓝色勾（第1步）+ 自动点最慢球（第2步）。"""
    from verify_auto.region_resolve import resolve_regions_learn
    from verify_auto.screen_detect import detect_step_fast, invalidate_step_cache

    step1_count = 0
    step2_count = 0
    saved_step1: set[str] = set()
    step1_saved_this_round = False
    step2_saved_this_round = False
    round_id = 0
    last_locate = 0.0
    prev_step = 0
    last_status_log = 0.0
    kw_override = keyword_override.strip()
    ctx = _LearnCtx()

    def progress(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    progress("持续收录 v0.5.3：第1步点图即收录 | 第2步识别「运动最慢」后自动点击")

    listener = _start_grid_listener(ctx, stop_event)

    try:
        while not stop_event.is_set():
            now = time.time()
            force_relocate = prev_step == 1 and ctx.step == 0
            if ctx.regions is None or now - last_locate >= LOCATE_REFRESH_SEC or force_relocate:
                hint = 2 if prev_step >= 1 else 0
                resolved = resolve_regions_learn(cfg, step_hint=hint, force_relocate=force_relocate)
                last_locate = now
                if resolved.ok and resolved.regions:
                    with ctx.lock:
                        ctx.regions = resolved.regions
                else:
                    if now - last_status_log > 3.0:
                        progress("等待验证小窗… 请先弹出验证码并框选区域")
                        last_status_log = now
                    stop_event.wait(LEARN_POLL_SEC)
                    continue

            with ctx.lock:
                regions = ctx.regions
            if not regions:
                stop_event.wait(LEARN_POLL_SEC)
                continue

            step, prompt_text = detect_step_fast(regions.prompt)

            if step != prev_step:
                invalidate_step_cache()
                if step == 2 and prev_step == 1:
                    progress(f"[切换第2步] {prompt_text[:40] or '运动最慢'}")
                    step2_saved_this_round = False
                    resolved = resolve_regions_learn(cfg, step_hint=2, force_relocate=True)
                    if resolved.ok and resolved.regions:
                        with ctx.lock:
                            ctx.regions = resolved.regions
                        regions = resolved.regions
                elif step == 1 and prev_step != 1:
                    progress(f"[切换第1步] {prompt_text[:40] or '选择最符合'}")
                    step1_saved_this_round = False
                    round_id += 1
                prev_step = step

            with ctx.lock:
                ctx.step = step

            if step == 1:
                pending_cell = None
                with ctx.lock:
                    if ctx.pending_cell is not None:
                        pending_cell = ctx.pending_cell
                        ctx.pending_cell = None

                if pending_cell is not None and not step1_saved_this_round:
                    saved, _ = _try_save_step1(
                        ctx,
                        cell_index=pending_cell,
                        kw_override=kw_override,
                        saved_step1=saved_step1,
                        round_id=round_id,
                        on_progress=progress,
                    )
                    if saved:
                        step1_count += 1
                        step1_saved_this_round = True

                if not step1_saved_this_round:
                    hit = detect_step1_selected_from_region(regions.grid)
                    if hit:
                        cell_index, conf = hit
                        if conf >= STEP1_MARKER_THRESHOLD:
                            saved, _ = _try_save_step1(
                                ctx,
                                cell_index=cell_index,
                                kw_override=kw_override,
                                saved_step1=saved_step1,
                                round_id=round_id,
                                on_progress=progress,
                            )
                            if saved:
                                step1_count += 1
                                step1_saved_this_round = True
                                progress(f"  (蓝色勾 conf={conf:.2f})")

            elif step == 2 and not step2_saved_this_round:
                if _collect_step2_with_click(cfg, regions, on_progress=progress):
                    step2_count += 1
                    step2_saved_this_round = True
                    progress(f"[第2步] 收录完成 (累计{step2_count})")
                stop_event.wait(0.08)
                continue

            elif step == 0 and now - last_status_log > 4.0:
                snippet = (prompt_text or "").replace("\n", " ")[:50]
                progress(f"等待验证… OCR: {snippet or '(空)'}")
                last_status_log = now

            stop_event.wait(LEARN_POLL_SEC)
    finally:
        listener.stop()

    msg = f"收录结束：第1步 {step1_count} 张，第2步 {step2_count} 张"
    return LearnResult(
        step1_count + step2_count > 0,
        msg,
        step1_count=step1_count,
        step2_count=step2_count,
    )


def _save_ball_crop_at(ball_region: Region, lx: int, ly: int, meta: dict | None = None) -> tuple[str, str]:
    scene = grab_region(ball_region)
    size = 48
    h, w = scene.shape[:2]
    x1 = max(0, lx - size // 2)
    y1 = max(0, ly - size // 2)
    x2 = min(w, lx + size // 2)
    y2 = min(h, ly + size // 2)
    crop = scene[y1:y2, x1:x2].copy()
    ball_path = save_step2_ball_crop(crop)
    scene_path = save_step2_scene(scene, lx, ly, meta or {})
    return str(ball_path), str(scene_path)


def learn_step1_auto_pass(
    cfg: dict,
    *,
    keyword_override: str = "",
    rows: int = 2,
    cols: int = 3,
    timeout_sec: float = 300.0,
    stop_event: threading.Event | None = None,
) -> LearnResult:
    """持续收录第1步，直到超时或 stop_event。"""
    ev = stop_event or threading.Event()
    if stop_event is None:

        def _auto_stop() -> None:
            time.sleep(timeout_sec)
            ev.set()

        threading.Thread(target=_auto_stop, daemon=True).start()
    return learn_watch_loop(cfg, ev, keyword_override=keyword_override)


def learn_step2_auto_motion(
    cfg: dict,
    *,
    ball_frames: int = STEP2_FAST_FRAMES,
    ball_interval_ms: int = STEP2_FAST_INTERVAL_MS,
    timeout_sec: float = 300.0,
    stop_event: threading.Event | None = None,
) -> LearnResult:
    """第2步：自动判断界面并收录最慢动球（可连续多次）。"""
    ev = stop_event or threading.Event()
    if stop_event is None:

        def _auto_stop() -> None:
            time.sleep(timeout_sec)
            ev.set()

        threading.Thread(target=_auto_stop, daemon=True).start()
    return learn_watch_loop(cfg, ev)


def learn_both_auto_pass(
    cfg: dict,
    *,
    keyword_override: str = "",
    stop_event: threading.Event | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> LearnResult:
    """持续收录两步（推荐）。"""
    ev = stop_event or threading.Event()
    if stop_event is None:

        def _auto_stop() -> None:
            time.sleep(300)
            ev.set()

        threading.Thread(target=_auto_stop, daemon=True).start()
    return learn_watch_loop(cfg, ev, keyword_override=keyword_override, on_progress=on_progress)


def learn_step1_cell(
    prompt_region: Region,
    grid_region: Region,
    cell_index: int,
    *,
    keyword: str = "",
    rows: int = 2,
    cols: int = 3,
) -> LearnResult:
    if cell_index < 0 or cell_index >= rows * cols:
        return LearnResult(False, f"格子序号无效: {cell_index + 1}")

    prompt_img = grab_region(prompt_region)
    grid_img = grab_region(grid_region)
    kw = keyword.strip() or extract_keyword(ocr_image(prompt_img))
    if not kw:
        return LearnResult(False, "没有关键词，请手动填写（如：兔子）")

    cells = split_grid(grid_img, rows, cols)
    path = save_step1_image(kw, cells[cell_index])
    return LearnResult(True, f"已保存到词库「{kw}」第 {cell_index + 1} 格", path=str(path))


def learn_step2_click_once(
    ball_region: Region,
    on_done,
) -> None:
    """等用户在屏幕上点一下（点最慢的那个球），自动截图入库。"""
    from pynput import mouse

    def on_click(x, y, button, pressed):
        if not pressed or button != mouse.Button.left:
            return
        r = ball_region
        if not (r.left <= x <= r.left + r.width and r.top <= y <= r.top + r.height):
            return
        scene = grab_region(ball_region)
        lx, ly = int(x) - r.left, int(y) - r.top
        size = 48
        h, w = scene.shape[:2]
        x1 = max(0, lx - size // 2)
        y1 = max(0, ly - size // 2)
        x2 = min(w, lx + size // 2)
        y2 = min(h, ly + size // 2)
        crop = scene[y1:y2, x1:x2].copy()
        ball_path = save_step2_ball_crop(crop)
        scene_path = save_step2_scene(scene, lx, ly, {"screen_x": int(x), "screen_y": int(y)})
        on_done(
            LearnResult(
                True,
                f"已收录动球 {ball_path.name} + 场景 {scene_path.name}",
                path=str(ball_path),
            )
        )
        return False

    listener = mouse.Listener(on_click=on_click)
    listener.start()

    def wait_stop():
        listener.join()

    threading.Thread(target=wait_stop, daemon=True).start()


def learn_step1_from_marker(
    prompt_region: Region,
    grid_region: Region,
    *,
    keyword: str = "",
    rows: int = 2,
    cols: int = 3,
    timeout_sec: float = 45.0,
) -> LearnResult:
    """等你在验证里点选图片出现蓝色勾后，自动识别格子并入库。"""
    hit = wait_for_step1_marker(grid_region, rows=rows, cols=cols, timeout_sec=timeout_sec)
    if not hit:
        return LearnResult(False, "超时：未检测到蓝色勾。请先在验证里点一张图")

    cell_index, conf = hit
    prompt_img = grab_region(prompt_region)
    grid_img = grab_region(grid_region)
    kw = keyword.strip() or extract_keyword(ocr_image(prompt_img))
    if not kw:
        return LearnResult(False, "没有关键词，请手动填写（如：柠檬）")

    cells = split_grid(grid_img, rows, cols)
    path = save_step1_image(kw, cells[cell_index])
    return LearnResult(
        True,
        f"已从蓝色勾识别第 {cell_index + 1} 格 (conf={conf:.2f})，保存到「{kw}」",
        path=str(path),
    )


def learn_step2_from_marker(
    ball_region: Region,
    *,
    timeout_sec: float = 45.0,
) -> LearnResult:
    """等你在第2步点最慢球出现蓝色数字圈后，自动截图入库。"""
    hit = wait_for_step2_marker(ball_region, timeout_sec=timeout_sec)
    if not hit:
        return LearnResult(False, "超时：未检测到蓝色选中圈。请先在验证里点最慢的球")

    lx, ly, conf = hit
    ball_path, scene_path = _save_ball_crop_at(
        ball_region,
        lx,
        ly,
        {
            "screen_x": ball_region.left + lx,
            "screen_y": ball_region.top + ly,
            "marker_conf": round(conf, 3),
            "source": "blue_badge",
        },
    )
    return LearnResult(
        True,
        f"已从蓝色圈识别动球 (conf={conf:.2f}) {ball_path} + {scene_path}",
        path=ball_path,
    )
