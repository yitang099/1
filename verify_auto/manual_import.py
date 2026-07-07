"""手动截图收录：框选区域 → 填关键字 → 存入词库文件夹。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from slider_solver.screen_match import Region, grab_region, save_region_image
from verify_auto.library_store import (
    list_step1_keywords,
    list_step2_tags,
    save_step1_image,
    save_step2_tagged_image,
)


@dataclass
class ManualImportResult:
    ok: bool
    message: str
    path: str = ""
    keyword: str = ""


def _read_image_file(path: str | Path) -> np.ndarray | None:
    p = Path(path)
    if not p.is_file():
        return None
    return cv2.imdecode(np.fromfile(str(p), dtype=np.uint8), cv2.IMREAD_COLOR)


def import_step1_region(region: Region, keyword: str, *, name: str = "") -> ManualImportResult:
    kw = keyword.strip()
    if not kw:
        return ManualImportResult(False, "请填写关键词，例如：柠檬、兔子")
    img = grab_region(region)
    if img is None or img.size == 0:
        return ManualImportResult(False, "截图失败，区域无效")
    path = save_step1_image(kw, img, name=name)
    return ManualImportResult(
        True,
        f"第1步已收录「{kw}」→ {path.name}",
        path=str(path),
        keyword=kw,
    )


def import_step1_file(file_path: str | Path, keyword: str, *, name: str = "") -> ManualImportResult:
    kw = keyword.strip()
    if not kw:
        return ManualImportResult(False, "请填写关键词，例如：柠檬、兔子")
    img = _read_image_file(file_path)
    if img is None:
        return ManualImportResult(False, f"无法读取图片: {file_path}")
    path = save_step1_image(kw, img, name=name or Path(file_path).name)
    return ManualImportResult(
        True,
        f"第1步已导入「{kw}」→ {path.name}",
        path=str(path),
        keyword=kw,
    )


def import_step2_region(region: Region, tag: str, *, name: str = "", note: str = "") -> ManualImportResult:
    """第2步：框选动球/场景截图，填标签后存入 library/step2/{标签}/"""
    tg = tag.strip() or "动球"
    img = grab_region(region)
    if img is None or img.size == 0:
        return ManualImportResult(False, "截图失败，区域无效")
    path = save_step2_tagged_image(tg, img, name=name, note=note)
    return ManualImportResult(
        True,
        f"第2步已收录「{tg}」→ {path.name}",
        path=str(path),
        keyword=tg,
    )


def import_step2_file(file_path: str | Path, tag: str, *, name: str = "", note: str = "") -> ManualImportResult:
    tg = tag.strip() or "动球"
    img = _read_image_file(file_path)
    if img is None:
        return ManualImportResult(False, f"无法读取图片: {file_path}")
    path = save_step2_tagged_image(tg, img, name=name or Path(file_path).name, note=note)
    return ManualImportResult(
        True,
        f"第2步已导入「{tg}」→ {path.name}",
        path=str(path),
        keyword=tg,
    )


def save_region_preview(region: Region, out_path: Path) -> bool:
    try:
        save_region_image(region, out_path)
        return True
    except Exception:
        return False


def library_summary() -> str:
    s1 = list_step1_keywords()
    s2 = list_step2_tags()
    lines = [f"第1步词库 {len(s1)} 个: {', '.join(s1) or '无'}"]
    lines.append(f"第2步词库 {len(s2)} 个: {', '.join(s2) or '无'}")
    return " | ".join(lines)
