"""手动学习：把当前屏收录进词库文件夹。"""
from __future__ import annotations

import threading
from dataclasses import dataclass

from pynput import mouse

from slider_solver.screen_match import Region, grab_region
from verify_auto.library_store import save_step1_image, save_step2_ball_crop, save_step2_scene
from verify_auto.selection_marker import wait_for_step1_marker, wait_for_step2_marker
from verify_auto.step1_pick import extract_keyword, ocr_image, split_grid


@dataclass
class LearnResult:
    ok: bool
    message: str
    path: str = ""


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
    scene = grab_region(ball_region)
    size = 48
    h, w = scene.shape[:2]
    x1 = max(0, lx - size // 2)
    y1 = max(0, ly - size // 2)
    x2 = min(w, lx + size // 2)
    y2 = min(h, ly + size // 2)
    crop = scene[y1:y2, x1:x2].copy()
    ball_path = save_step2_ball_crop(crop)
    scene_path = save_step2_scene(
        scene,
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
        f"已从蓝色圈识别动球 (conf={conf:.2f}) {ball_path.name} + {scene_path.name}",
        path=str(ball_path),
    )
