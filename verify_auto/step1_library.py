"""第1步：用词库文件夹匹配（用户手动存图）。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from slider_solver.screen_match import Region, grab_region
from verify_auto.library_store import list_step1_keywords, match_cell_library, step1_keyword_dir
from verify_auto.step1_pick import cell_centers, extract_keyword, ocr_image, split_grid


@dataclass
class Step1LibResult:
    ok: bool
    message: str
    keyword: str = ""
    cell_index: int = -1
    click_x: int = 0
    click_y: int = 0
    score: float = 0.0
    ref_file: str = ""


def run_step1_library(
    prompt_region: Region,
    grid_region: Region,
    *,
    keyword_override: str = "",
    rows: int = 2,
    cols: int = 3,
    min_score: float = 0.72,
) -> Step1LibResult:
    prompt_img = grab_region(prompt_region)
    grid_img = grab_region(grid_region)
    text = ocr_image(prompt_img)
    keyword = keyword_override or extract_keyword(text)

    if not keyword:
        kws = list_step1_keywords()
        return Step1LibResult(
            False,
            f"未读到提示词。请建词库文件夹或手动填关键词。已有词库: {', '.join(kws) or '无'}",
        )

    lib_dir = step1_keyword_dir(keyword)
    refs = list(lib_dir.glob("*"))
    refs = [p for p in refs if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".webp")]
    if not refs:
        return Step1LibResult(
            False,
            f"词库「{keyword}」里没有图片。请把正确图放进: {lib_dir}",
            keyword=keyword,
        )

    cells = split_grid(grid_img, rows, cols)
    centers = cell_centers(grid_region, rows, cols)

    best_i = -1
    best_score = 0.0
    best_ref = ""
    for i, cell in enumerate(cells):
        score, ref = match_cell_library(cell, keyword)
        if score > best_score:
            best_score = score
            best_i = i
            best_ref = ref

    if best_i < 0 or best_score < min_score:
        return Step1LibResult(
            False,
            f"词库未匹配到（最高 {best_score:.2f} < {min_score}）。请往 {lib_dir} 添加更多正确图",
            keyword=keyword,
            score=best_score,
        )

    cx, cy = centers[best_i]
    return Step1LibResult(
        True,
        f"词库匹配「{keyword}」第 {best_i + 1} 格 score={best_score:.2f} ref={best_ref}",
        keyword=keyword,
        cell_index=best_i,
        click_x=cx,
        click_y=cy,
        score=best_score,
        ref_file=best_ref,
    )
