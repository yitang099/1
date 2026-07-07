"""手动学习：把当前屏收录进词库文件夹。"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from pynput import mouse

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
    timeout_sec: float = 90.0,
) -> LearnResult:
    """你手动选对图并点确定：出现蓝色勾时自动 OCR 关键词 + 保存该格图片。"""
    from verify_auto.region_resolve import resolve_regions
    from verify_auto.screen_detect import detect_step

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        resolved = resolve_regions(cfg, step_hint=1)
        if not resolved.ok or not resolved.regions:
            time.sleep(0.45)
            continue

        prompt = resolved.regions.prompt
        grid = resolved.regions.grid
        if detect_step(prompt) != 1:
            time.sleep(0.45)
            continue

        hit = detect_step1_selected_from_region(grid, rows=rows, cols=cols)
        if not hit:
            time.sleep(0.45)
            continue

        cell_index, conf = hit
        prompt_img = grab_region(prompt)
        grid_img = grab_region(grid)
        kw = keyword_override.strip() or extract_keyword(ocr_image(prompt_img))
        if not kw:
            time.sleep(0.45)
            continue

        cells = split_grid(grid_img, rows, cols)
        path = save_step1_image(kw, cells[cell_index])
        return LearnResult(
            True,
            f"已自动收录「{kw}」第 {cell_index + 1} 格 (勾 conf={conf:.2f})",
            path=str(path),
        )

    return LearnResult(False, "超时：请先在验证里选对图片（出现蓝色勾），再点确定")


def learn_step2_auto_motion(
    cfg: dict,
    *,
    ball_frames: int = 15,
    ball_interval_ms: int = 100,
    timeout_sec: float = 90.0,
) -> LearnResult:
    """第2步标题固定，自动帧差分找最慢动球并收录（不用手点）。"""
    from verify_auto.ball_slowest import find_slowest_moving_ball
    from verify_auto.region_resolve import resolve_regions
    from verify_auto.screen_detect import detect_step

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        resolved = resolve_regions(cfg, step_hint=2)
        if not resolved.ok or not resolved.regions:
            time.sleep(0.5)
            continue

        prompt = resolved.regions.prompt
        ball = resolved.regions.ball
        if detect_step(prompt) != 2:
            time.sleep(0.5)
            continue

        r = find_slowest_moving_ball(ball, frames=ball_frames, interval_ms=ball_interval_ms)
        if not r.ok:
            time.sleep(0.8)
            continue

        lx = r.click_x - ball.left
        ly = r.click_y - ball.top
        ball_path, scene_path = _save_ball_crop_at(
            ball,
            lx,
            ly,
            {
                "screen_x": r.click_x,
                "screen_y": r.click_y,
                "total_move_px": r.movers,
                "source": "auto_motion",
            },
        )
        return LearnResult(
            True,
            f"已自动收录最慢动球 {ball_path} (移动={r.message})",
            path=ball_path,
        )

    return LearnResult(False, "超时：未等到第2步，或未检测到动球")


def learn_both_auto_pass(
    cfg: dict,
    *,
    keyword_override: str = "",
    ball_frames: int = 15,
    ball_interval_ms: int = 100,
    timeout_sec: float = 120.0,
) -> LearnResult:
    """一次监听：第1步你点对+确定后收录图，第2步自动找最慢球收录。"""
    start = time.time()
    step1_timeout = min(75.0, timeout_sec * 0.55)
    r1 = learn_step1_auto_pass(
        cfg,
        keyword_override=keyword_override,
        timeout_sec=step1_timeout,
    )
    if not r1.ok:
        return r1

    from verify_auto.region_resolve import resolve_regions
    from verify_auto.screen_detect import detect_step

    wait_deadline = start + timeout_sec
    while time.time() < wait_deadline:
        resolved = resolve_regions(cfg, step_hint=2)
        if resolved.ok and resolved.regions and detect_step(resolved.regions.prompt) == 2:
            break
        time.sleep(0.4)
    else:
        return LearnResult(False, f"第1步已收录；但未等到第2步界面。{r1.message}")

    remain = max(15.0, wait_deadline - time.time())
    r2 = learn_step2_auto_motion(
        cfg,
        ball_frames=ball_frames,
        ball_interval_ms=ball_interval_ms,
        timeout_sec=remain,
    )
    if not r2.ok:
        return LearnResult(False, f"{r1.message} | 第2步失败：{r2.message}")
    return LearnResult(True, f"{r1.message} | {r2.message}", path=r2.path)


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
