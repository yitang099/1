"""第2步手动收录：截全景(所有球) → 用户点击慢球 → 裁切保存。"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np

from slider_solver.screen_match import Region, grab_region
from verify_auto.ball_slowest import find_circles_in_image
from verify_auto.library_store import save_step2_scene, save_step2_tagged_image
from verify_auto.manual_import import ManualImportResult


def _crop_ball(bgr: np.ndarray, cx: int, cy: int, radius: int | None = None) -> np.ndarray:
    h, w = bgr.shape[:2]
    half = max(20, int((radius or 22) * 1.15))
    x1 = max(0, cx - half)
    y1 = max(0, cy - half)
    x2 = min(w, cx + half)
    y2 = min(h, cy + half)
    return bgr[y1:y2, x1:x2].copy()


def _nearest_circle(
    circles: list[tuple[int, int, int]], lx: int, ly: int
) -> tuple[int, int, int] | None:
    if not circles:
        return None
    return min(circles, key=lambda c: (c[0] - lx) ** 2 + (c[1] - ly) ** 2)


def capture_step2_scene(
    region: Region,
    *,
    other_tag: str = "动球",
    on_progress: Callable[[str], None] | None = None,
) -> tuple[np.ndarray, str, list[tuple[int, int, int]], list[str]]:
    """
    截取含所有球的区域，自动识别每个球并分别保存。
    返回 (场景图, 时间戳id, 圆列表, 已保存的动球路径)。
    """
    scene = grab_region(region)
    if scene is None or scene.size == 0:
        raise ValueError("截图失败")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    circles = find_circles_in_image(scene)
    ball_paths: list[str] = []

    for i, (cx, cy, rad) in enumerate(circles):
        crop = _crop_ball(scene, cx, cy, rad)
        path = save_step2_tagged_image(other_tag, crop, name=f"{ts}_ball{i + 1}.png")
        ball_paths.append(str(path))

    meta = {
        "source": "scene_all_balls",
        "region": region.as_dict(),
        "balls": [{"cx": cx, "cy": cy, "r": rad, "index": i} for i, (cx, cy, rad) in enumerate(circles)],
        "ball_files": ball_paths,
    }
    scene_path = save_step2_scene(scene, 0, 0, meta, ts=ts)
    if on_progress:
        on_progress(f"[第2步] 全景已保存: {scene_path.name}")
        on_progress(f"[第2步] 识别到 {len(circles)} 个球，已存入「{other_tag}」文件夹")
        on_progress("[第2步] 现在请在验证码里点击【最慢的那个球】")
    return scene, ts, circles, ball_paths, str(scene_path)


def wait_click_slowest_ball(
    region: Region,
    scene: np.ndarray,
    scene_ts: str,
    circles: list[tuple[int, int, int]],
    *,
    slow_tag: str = "慢球",
    on_done: Callable[[ManualImportResult], None],
    on_progress: Callable[[str], None] | None = None,
    timeout_sec: float = 120.0,
) -> None:
    """等待用户在球区内点击最慢的球，裁切后保存为慢球。"""
    from pynput import mouse

    done = threading.Event()
    scene_path = None

    def progress(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    progress("[第2步] 等待你点击最慢的那个球…")

    def on_click(x, y, button, pressed):
        nonlocal scene_path
        if done.is_set():
            return False
        if not pressed or button != mouse.Button.left:
            return
        if not (region.left <= x < region.left + region.width and region.top <= y < region.top + region.height):
            progress("[!] 点击不在球区内，请点在球区域里")
            return

        lx, ly = int(x) - region.left, int(y) - region.top
        hit = _nearest_circle(circles, lx, ly)
        if hit:
            cx, cy, rad = hit
            dist = ((cx - lx) ** 2 + (cy - ly) ** 2) ** 0.5
            if dist > max(rad * 2.5, 50):
                cx, cy, rad = lx, ly, 22
        else:
            cx, cy, rad = lx, ly, 22

        crop = _crop_ball(scene, cx, cy, rad)
        slow_path = save_step2_tagged_image(
            slow_tag,
            crop,
            name=f"{scene_ts}_慢球.png",
            note=f"click=({lx},{ly}) nearest=({cx},{cy})",
        )

        # 更新场景 json
        from verify_auto.library_store import STEP2_SCENES_DIR

        json_path = STEP2_SCENES_DIR / f"scene_{scene_ts}.json"
        png_path = STEP2_SCENES_DIR / f"scene_{scene_ts}.png"
        if json_path.is_file():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                data["slowest"] = {"cx": cx, "cy": cy, "r": rad, "click_x": lx, "click_y": ly}
                data["slow_ball_file"] = str(slow_path)
                json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                scene_path = str(png_path)
            except Exception:
                pass

        done.set()
        on_done(
            ManualImportResult(
                True,
                f"慢球已收录 → {slow_path.name}（共识别 {len(circles)} 个球）",
                path=str(slow_path),
                keyword=slow_tag,
            )
        )
        return False

    listener = mouse.Listener(on_click=on_click)
    listener.start()

    def watchdog():
        listener.join(timeout_sec)
        if not done.is_set():
            done.set()
            listener.stop()
            on_done(ManualImportResult(False, "超时：未检测到点击。请重试"))

    threading.Thread(target=watchdog, daemon=True).start()


def start_step2_click_learn(
    region: Region,
    *,
    slow_tag: str = "慢球",
    other_tag: str = "动球",
    on_done: Callable[[ManualImportResult], None],
    on_progress: Callable[[str], None] | None = None,
    timeout_sec: float = 120.0,
) -> None:
    """完整流程：截全景+所有球 → 等用户点慢球 → 保存。"""

    def work():
        try:
            scene, ts, circles, _, _ = capture_step2_scene(
                region, other_tag=other_tag, on_progress=on_progress
            )
            wait_click_slowest_ball(
                region,
                scene,
                ts,
                circles,
                slow_tag=slow_tag,
                on_done=on_done,
                on_progress=on_progress,
                timeout_sec=timeout_sec,
            )
        except Exception as exc:
            on_done(ManualImportResult(False, str(exc)))

    threading.Thread(target=work, daemon=True, name="step2-click-learn").start()
