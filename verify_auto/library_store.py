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
STEP2_TAGS_DIR = STEP2_DIR / "tags"


def ensure_library() -> None:
    for d in (STEP1_DIR, STEP2_DIR, STEP2_BALLS_DIR, STEP2_SCENES_DIR, STEP2_TAGS_DIR):
        d.mkdir(parents=True, exist_ok=True)

    readme1 = STEP1_DIR / "【说明】把正确图片放进对应词文件夹.txt"
    if not readme1.exists():
        readme1.write_text(
            "第1步词库用法：\n"
            "方式A（推荐）：工具里点「第1步：框选截图」→ 框正确图 → 填关键词「柠檬」\n"
            "方式B：自己截图后点「从文件导入第1步」→ 填关键词\n"
            "方式C：手动建文件夹 step1/柠檬/ ，把 png 放进去\n"
            "文件夹名 = 验证码提示词。可存多张图。\n",
            encoding="utf-8",
        )

    readme2 = STEP2_DIR / "【说明】第2步词库.txt"
    if not readme2.exists():
        readme2.write_text(
            "第2步词库用法：\n"
            "【推荐】点工具「第2步：截全图→点慢球」：\n"
            "  1. 框住所有球所在的区域（全景）\n"
            "  2. 工具自动截取并识别每个球，存入 tags/动球/\n"
            "  3. 你在验证码里点击【最慢的那个球】\n"
            "  4. 工具按点击位置裁切，存入 tags/慢球/\n"
            "也可手动把球截图放进 step2/tags/慢球/ 或 tags/动球/\n",
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


def step2_tag_dir(tag: str) -> Path:
    ensure_library()
    d = STEP2_TAGS_DIR / safe_keyword(tag)
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_step2_tags() -> list[str]:
    ensure_library()
    out: list[str] = []
    if STEP2_TAGS_DIR.is_dir():
        for p in STEP2_TAGS_DIR.iterdir():
            if p.is_dir() and not p.name.startswith("【"):
                out.append(p.name)
    return sorted(out)


def save_step2_tagged_image(tag: str, bgr: np.ndarray, *, name: str = "", note: str = "") -> Path:
    d = step2_tag_dir(tag)
    if not name:
        name = datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
    path = d / name
    cv2.imencode(".png", bgr)[1].tofile(str(path))
    if note.strip():
        meta = path.with_suffix(".json")
        meta.write_text(
            json.dumps({"tag": tag, "note": note.strip()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return path


def save_step1_image(keyword: str, bgr: np.ndarray, name: str = "") -> Path:
    d = step1_keyword_dir(keyword)
    if not name:
        name = datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
    path = d / name
    cv2.imencode(".png", bgr)[1].tofile(str(path))
    return path


def save_step2_ball_crop(bgr: np.ndarray, *, tag: str = "动球") -> Path:
    ensure_library()
    name = datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
    return save_step2_tagged_image(tag, bgr, name=name)


def save_step2_scene(
    scene_bgr: np.ndarray,
    slowest_x: int,
    slowest_y: int,
    meta: dict | None = None,
    *,
    ts: str = "",
) -> Path:
    ensure_library()
    if not ts:
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


def rank_cells_global_library(
    cells: list[np.ndarray],
    *,
    min_score: float = 0.55,
    top_n: int = 5,
) -> list[tuple[int, float, str, str]]:
    """全词库扫描：不依赖 OCR 关键词是否准确。返回 [(格子, 分数, 词文件夹, 参考图), ...]"""
    ensure_library()
    ranked: list[tuple[int, float, str, str]] = []
    for kw in list_step1_keywords():
        folder = step1_keyword_dir(kw)
        for i, cell in enumerate(cells):
            score, ref = match_against_folder(cell, folder)
            if score >= min_score:
                ranked.append((i, score, kw, ref))
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked[:top_n]


def list_step2_ball_templates() -> list[Path]:
    ensure_library()
    out: list[Path] = []
    for p in STEP2_BALLS_DIR.glob("*"):
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp"):
            out.append(p)
    for tag in list_step2_tags():
        out.extend(step2_tag_dir(tag).glob("*"))
    return out
