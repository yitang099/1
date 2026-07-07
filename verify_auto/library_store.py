"""词库目录 — 用户手动把图放进文件夹，后续按图匹配。"""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from verify_auto.config import LIBRARY_DIR

STEP1_DIR = LIBRARY_DIR / "step1"
STEP2_DIR = LIBRARY_DIR / "step2"
STEP2_BALLS_DIR = STEP2_DIR / "moving_balls"
STEP2_SCENES_DIR = STEP2_DIR / "scenes"


def ensure_library() -> None:
    for d in (STEP1_DIR, STEP2_DIR, STEP2_BALLS_DIR, STEP2_SCENES_DIR):
        d.mkdir(parents=True, exist_ok=True)

    readme1 = STEP1_DIR / "【说明】把正确图片放进对应词文件夹.txt"
    if not readme1.exists():
        readme1.write_text(
            "第1步词库用法：\n"
            "1. 在下面新建文件夹，名字 = 提示词，例如：兔子\n"
            "2. 每次你手动选对后，把【那一张正确图】保存进该文件夹\n"
            "3. 可以存多张同义词图，工具会比对相似度\n"
            "4. 例：step1/兔子/001.png  step1/兔子/002.png\n",
            encoding="utf-8",
        )

    readme2 = STEP2_DIR / "【说明】第2步词库.txt"
    if not readme2.exists():
        readme2.write_text(
            "第2步词库用法：\n"
            "1. moving_balls/ — 放【会动的球】截图（不要放不动的大装饰球）\n"
            "2. scenes/ — 放整屏第2步截图 + 同名的 .json 记录最慢球位置\n"
            "3. 工具仍会用帧差分找动球；词库帮助辨认哪些是动球\n",
            encoding="utf-8",
        )


def safe_keyword(name: str) -> str:
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name or "未命名"


def step1_keyword_dir(keyword: str) -> Path:
    ensure_library()
    d = STEP1_DIR / safe_keyword(keyword)
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_step1_keywords() -> list[str]:
    ensure_library()
    out = []
    for p in STEP1_DIR.iterdir():
        if p.is_dir() and not p.name.startswith("【"):
            out.append(p.name)
    return sorted(out)


def save_step1_image(keyword: str, bgr: np.ndarray, name: str = "") -> Path:
    d = step1_keyword_dir(keyword)
    if not name:
        name = datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
    path = d / name
    cv2.imencode(".png", bgr)[1].tofile(str(path))
    return path


def save_step2_ball_crop(bgr: np.ndarray) -> Path:
    ensure_library()
    name = datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
    path = STEP2_BALLS_DIR / name
    cv2.imencode(".png", bgr)[1].tofile(str(path))
    return path


def save_step2_scene(scene_bgr: np.ndarray, slowest_x: int, slowest_y: int, meta: dict | None = None) -> Path:
    ensure_library()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    img_path = STEP2_SCENES_DIR / f"scene_{ts}.png"
    json_path = STEP2_SCENES_DIR / f"scene_{ts}.json"
    cv2.imencode(".png", scene_bgr)[1].tofile(str(img_path))
    data = {"slowest_x": slowest_x, "slowest_y": slowest_y, **(meta or {})}
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return img_path


def _similarity(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        b = cv2.resize(b, (a.shape[1], a.shape[0]))
    res = cv2.matchTemplate(a, b, cv2.TM_CCOEFF_NORMED)
    return float(res.max())


def match_against_folder(cell_bgr: np.ndarray, folder: Path, threshold: float = 0.72) -> tuple[float, str]:
    best_score = 0.0
    best_name = ""
    if not folder.is_dir():
        return best_score, best_name
    for p in folder.glob("*"):
        if p.suffix.lower() not in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
            continue
        ref = cv2.imdecode(np.fromfile(str(p), dtype=np.uint8), cv2.IMREAD_COLOR)
        if ref is None:
            continue
        s = _similarity(cell_bgr, ref)
        if s > best_score:
            best_score = s
            best_name = p.name
    return best_score, best_name


def match_cell_library(cell_bgr: np.ndarray, keyword: str) -> tuple[float, str]:
    return match_against_folder(cell_bgr, step1_keyword_dir(keyword))


def list_step2_ball_templates() -> list[Path]:
    ensure_library()
    return [p for p in STEP2_BALLS_DIR.glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp")]
