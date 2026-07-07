"""第1步：读提示字 + 在 2x3 图格里选最符合的一张。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from slider_solver.screen_match import Region, grab_region, save_region_image


@dataclass
class Step1Result:
    ok: bool
    message: str
    keyword: str = ""
    cell_index: int = -1
    click_x: int = 0
    click_y: int = 0
    scores: list[float] | None = None


def extract_keyword(text: str) -> str:
    for pat in (
        r"[''『「]([^''』」]+)[''』」]",
        r"描述的图片[：:]\s*['']?([^'''\s]+)",
        r"图片[：:]\s*['']?([^'''\s]+)",
    ):
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    return ""


def ocr_image(bgr: np.ndarray) -> str:
    from verify_auto.ocr_util import ocr_text

    return ocr_text(bgr)


def split_grid(bgr: np.ndarray, rows: int = 2, cols: int = 3) -> list[np.ndarray]:
    h, w = bgr.shape[:2]
    cells: list[np.ndarray] = []
    for r in range(rows):
        for c in range(cols):
            x0, y0 = c * w // cols, r * h // rows
            x1, y1 = (c + 1) * w // cols, (r + 1) * h // rows
            cells.append(bgr[y0:y1, x0:x1].copy())
    return cells


def cell_centers(grid_region: Region, rows: int = 2, cols: int = 3) -> list[tuple[int, int]]:
    pts: list[tuple[int, int]] = []
    for r in range(rows):
        for c in range(cols):
            cx = grid_region.left + (c + 0.5) * grid_region.width / cols
            cy = grid_region.top + (r + 0.5) * grid_region.height / rows
            pts.append((int(cx), int(cy)))
    return pts


def _clip_scores(keyword: str, cells: list[np.ndarray]) -> list[float] | None:
    try:
        from PIL import Image
        from transformers import ChineseCLIPModel, ChineseCLIPProcessor
        import torch

        model_name = "OFA-Sys/chinese-clip-vit-base-patch16"
        processor = ChineseCLIPProcessor.from_pretrained(model_name)
        model = ChineseCLIPModel.from_pretrained(model_name)
        model.eval()

        texts = [keyword, f"一张{keyword}的照片", f"{keyword}的图片"]
        text_inputs = processor(text=texts, return_tensors="pt", padding=True)
        with torch.no_grad():
            text_feat = model.get_text_features(**text_inputs)
            text_feat = text_feat / text_feat.norm(dim=-1, keepdim=True)
            text_feat = text_feat.mean(dim=0, keepdim=True)

        scores: list[float] = []
        for cell in cells:
            rgb = cv2.cvtColor(cell, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(rgb)
            img_in = processor(images=pil, return_tensors="pt")
            with torch.no_grad():
                img_feat = model.get_image_features(**img_in)
                img_feat = img_feat / img_feat.norm(dim=-1, keepdim=True)
            sim = float((img_feat @ text_feat.T).squeeze().item())
            scores.append(sim)
        return scores
    except Exception:
        return None


def _hist_scores(keyword: str, cells: list[np.ndarray]) -> list[float]:
    """无 AI 时的弱兜底：绿色多→兔子等（很不准，仅备用）。"""
    scores: list[float] = []
    for cell in cells:
        hsv = cv2.cvtColor(cell, cv2.COLOR_BGR2HSV)
        green = cv2.inRange(hsv, (35, 40, 40), (85, 255, 255))
        brown = cv2.inRange(hsv, (10, 50, 40), (25, 200, 200))
        g_ratio = green.sum() / max(cell.size, 1)
        b_ratio = brown.sum() / max(cell.size, 1)
        if "兔" in keyword:
            scores.append(float(g_ratio * 2 + b_ratio))
        else:
            scores.append(float(cell.std()))
    return scores


def run_step1(
    prompt_region: Region,
    grid_region: Region,
    *,
    keyword_override: str = "",
    rows: int = 2,
    cols: int = 3,
    debug_dir: str | Path | None = None,
) -> Step1Result:
    prompt_img = grab_region(prompt_region)
    grid_img = grab_region(grid_region)

    text = ocr_image(prompt_img)
    keyword = keyword_override or extract_keyword(text)
    if not keyword:
        return Step1Result(False, f"未读到提示字，OCR={text[:80]!r}")

    cells = split_grid(grid_img, rows, cols)
    scores = _clip_scores(keyword, cells)
    method = "chinese-clip"
    if scores is None:
        scores = _hist_scores(keyword, cells)
        method = "hist-fallback"

    best = int(np.argmax(scores))
    centers = cell_centers(grid_region, rows, cols)
    cx, cy = centers[best]

    if debug_dir:
        p = Path(debug_dir)
        p.mkdir(parents=True, exist_ok=True)
        save_region_image(prompt_region, p / "step1_prompt.png")
        save_region_image(grid_region, p / "step1_grid.png")
        for i, cell in enumerate(cells):
            cv2.imencode(".png", cell)[1].tofile(str(p / f"cell_{i}.png"))

    return Step1Result(
        True,
        f"第1步 [{method}] 关键词「{keyword}」→ 选第 {best + 1} 格 (score={scores[best]:.3f})",
        keyword=keyword,
        cell_index=best,
        click_x=cx,
        click_y=cy,
        scores=scores,
    )
