"""手动学习：把当前屏收录进词库文件夹。"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from slider_solver.screen_match import Region, grab_region
from verify_auto.library_store import save_step1_image, save_step2_ball_crop, save_step2_scene
from verify_auto.selection_marker import (
    detect_step1_selected_from_region,
    wait_for_step1_marker,
    wait_for_step2_marker,
)
from verify_auto.step1_pick import extract_keyword, ocr_image, split_grid


@dataclass
class LearnResult:
    ok: bool
    message: str
    path: str = ""
    step1_count: int = 0
    step2_count: int = 0


LEARN_POLL_SEC = 1.0
LEARN_BALL_FRAMES = 6
LEARN_BALL_INTERVAL_MS = 120
LOCATE_REFRESH_SEC = 12.0


def _resolve_for_learn(cfg: dict, last_locate: float, force: bool = False) -> tuple[Any, float]:
    from verify_auto.region_resolve import resolve_regions

    now = time.time()
    if force or now - last_locate >= LOCATE_REFRESH_SEC:
        return resolve_regions(cfg, step_hint=0, force_refresh=True), now
    return resolve_regions(cfg, step_hint=0), last_locate


def learn_watch_loop(
    cfg: dict,
    stop_event: threading.Event,
    *,
    keyword_override: str = "",
    on_progress: Callable[[str], None] | None = None,
) -> LearnResult:
    """持续收录：自动识别第1/2步，可收多张，低 CPU 轮询。"""
    from verify_auto.ball_slowest import find_slowest_moving_ball
    from verify_auto.screen_detect import detect_step, invalidate_step_cache

    step1_count = 0
    step2_count = 0
    saved_step1: set[str] = set()
    step2_round_saved = False
    waiting_marker_clear = False
    last_locate = 0.0
    kw_override = keyword_override.strip()

    def progress(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    progress("持续收录中… 请正常过验证")

    while not stop_event.is_set():
        resolved, last_locate = _resolve_for_learn(cfg, last_locate)
        if not resolved.ok or not resolved.regions:
            stop_event.wait(LEARN_POLL_SEC)
            continue

        regions = resolved.regions
        step = detect_step(regions.prompt)
        if step == 0:
            stop_event.wait(LEARN_POLL_SEC)
            continue

        if step == 1:
            step2_round_saved = False
            if waiting_marker_clear:
                if not detect_step1_selected_from_region(regions.grid):
                    waiting_marker_clear = False
                    invalidate_step_cache()
                stop_event.wait(LEARN_POLL_SEC)
                continue

            hit = detect_step1_selected_from_region(regions.grid)
            if hit:
                cell_index, _conf = hit
                kw = kw_override or extract_keyword(ocr_image(grab_region(regions.prompt)))
                if kw:
                    sig = f"{kw}#{cell_index}"
                    if sig not in saved_step1:
                        cells = split_grid(grab_region(regions.grid))
                        save_step1_image(kw, cells[cell_index])
                        saved_step1.add(sig)
                        step1_count += 1
                        waiting_marker_clear = True
                        progress(f"[第1步] 「{kw}」第{cell_index + 1}格 (累计{step1_count})")

        elif step == 2 and not step2_round_saved:
            progress("[第2步] 分析最慢动球…")
            r = find_slowest_moving_ball(
                regions.ball,
                frames=LEARN_BALL_FRAMES,
                interval_ms=LEARN_BALL_INTERVAL_MS,
            )
            if r.ok:
                lx = r.click_x - regions.ball.left
                ly = r.click_y - regions.ball.top
                _save_ball_crop_at(
                    regions.ball,
                    lx,
                    ly,
                    {"source": "auto_motion", "screen_x": r.click_x, "screen_y": r.click_y},
                )
                step2_count += 1
                step2_round_saved = True
                progress(f"[第2步] 已收录最慢动球 (累计{step2_count})")

        stop_event.wait(LEARN_POLL_SEC)

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
    from verify_auto.screen_detect import detect_step, invalidate_step_cache

    deadline = time.time() + timeout_sec
    saved: set[str] = set()
    count = 0
    waiting_clear = False
    last_locate = 0.0
    kw_override = keyword_override.strip()

    while time.time() < deadline and not (stop_event and stop_event.is_set()):
        resolved, last_locate = _resolve_for_learn(cfg, last_locate)
        if not resolved.ok or not resolved.regions:
            time.sleep(LEARN_POLL_SEC)
            continue

        prompt, grid = resolved.regions.prompt, resolved.regions.grid
        if detect_step(prompt) != 1:
            time.sleep(LEARN_POLL_SEC)
            continue

        if waiting_clear:
            if not detect_step1_selected_from_region(grid, rows=rows, cols=cols):
                waiting_clear = False
                invalidate_step_cache()
            time.sleep(LEARN_POLL_SEC)
            continue

        hit = detect_step1_selected_from_region(grid, rows=rows, cols=cols)
        if not hit:
            time.sleep(LEARN_POLL_SEC)
            continue

        cell_index, conf = hit
        kw = kw_override or extract_keyword(ocr_image(grab_region(prompt)))
        if not kw:
            time.sleep(LEARN_POLL_SEC)
            continue

        sig = f"{kw}#{cell_index}"
        if sig in saved:
            time.sleep(LEARN_POLL_SEC)
            continue

        cells = split_grid(grab_region(grid), rows, cols)
        save_step1_image(kw, cells[cell_index])
        saved.add(sig)
        count += 1
        waiting_clear = True

    if count:
        return LearnResult(True, f"第1步共收录 {count} 张", step1_count=count)
    return LearnResult(False, "未收录到图片（请选对出现蓝色勾）")


def learn_step2_auto_motion(
    cfg: dict,
    *,
    ball_frames: int = LEARN_BALL_FRAMES,
    ball_interval_ms: int = LEARN_BALL_INTERVAL_MS,
    timeout_sec: float = 300.0,
    stop_event: threading.Event | None = None,
) -> LearnResult:
    """第2步：自动判断界面并收录最慢动球（可连续多次）。"""
    from verify_auto.screen_detect import detect_step, invalidate_step_cache

    deadline = time.time() + timeout_sec
    count = 0
    last_locate = 0.0
    step2_round_saved = False

    while time.time() < deadline and not (stop_event and stop_event.is_set()):
        resolved, last_locate = _resolve_for_learn(cfg, last_locate)
        if not resolved.ok or not resolved.regions:
            time.sleep(LEARN_POLL_SEC)
            continue

        step = detect_step(resolved.regions.prompt)
        if step == 1:
            step2_round_saved = False
            invalidate_step_cache()
            time.sleep(LEARN_POLL_SEC)
            continue
        if step != 2:
            time.sleep(LEARN_POLL_SEC)
            continue
        if step2_round_saved:
            time.sleep(LEARN_POLL_SEC)
            continue

        from verify_auto.ball_slowest import find_slowest_moving_ball

        r = find_slowest_moving_ball(
            resolved.regions.ball,
            frames=ball_frames,
            interval_ms=ball_interval_ms,
        )
        if not r.ok:
            time.sleep(LEARN_POLL_SEC)
            continue

        lx = r.click_x - resolved.regions.ball.left
        ly = r.click_y - resolved.regions.ball.top
        ball_path, _ = _save_ball_crop_at(
            resolved.regions.ball,
            lx,
            ly,
            {"source": "auto_motion", "screen_x": r.click_x, "screen_y": r.click_y},
        )
        count += 1
        step2_round_saved = True

    if count:
        return LearnResult(True, f"第2步共收录 {count} 张", step2_count=count)
    return LearnResult(False, "未收录到动球（请等到第2步界面）")


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
        # 兼容旧调用：跑 5 分钟后自动停
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
