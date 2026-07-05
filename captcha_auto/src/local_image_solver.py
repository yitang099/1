import os
import re

import numpy as np
from PIL import Image

_ocr = None


def _get_ocr():
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr = RapidOCR()
    return _ocr


def extract_question(img_rgb, title_ratio=0.24):
    h, w = img_rgb.shape[:2]
    title = img_rgb[: max(24, int(h * title_ratio)), :]
    ocr = _get_ocr()
    result, _ = ocr(title)
    if not result:
        return ""

    text = " ".join(str(item[1]) for item in result)
    text = text.replace(" ", "")

    for pat in [
        r"[「『\"']([^」』\"']+)[」』\"']",
        r"[:：]['\"]?([^'\"]+)['\"]?$",
        r"描述[的:]?(.+)$",
    ]:
        m = re.search(pat, text)
        if m:
            q = m.group(1).strip().strip("'\"")
            if len(q) >= 2:
                return q
    return text


def _split_grid(img_rgb, cols=3, rows=2, title_ratio=0.24, pad=4):
    h, w = img_rgb.shape[:2]
    body_top = int(h * title_ratio)
    body = img_rgb[body_top:, :]
    bh, bw = body.shape[:2]
    cell_w = bw // cols
    cell_h = bh // rows
    cells = []
    for r in range(rows):
        for c in range(cols):
            y1 = r * cell_h + pad
            x1 = c * cell_w + pad
            y2 = (r + 1) * cell_h - pad
            x2 = (c + 1) * cell_w - pad
            cell = body[y1:y2, x1:x2]
            cx = int(c * cell_w + cell_w / 2)
            cy = int(body_top + r * cell_h + cell_h / 2)
            cells.append((cell, cx, cy))
    return cells


_clip_model = None
_clip_processor = None


def _get_clip():
    global _clip_model, _clip_processor
    if _clip_model is None:
        import torch
        from transformers import ChineseCLIPModel, ChineseCLIPProcessor

        name = "OFA-Sys/chinese-clip-vit-base-patch16"
        cache = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        os.makedirs(cache, exist_ok=True)
        _clip_processor = ChineseCLIPProcessor.from_pretrained(name, cache_dir=cache)
        _clip_model = ChineseCLIPModel.from_pretrained(name, cache_dir=cache)
        _clip_model.eval()
        _clip_model.to("cpu")
    return _clip_model, _clip_processor


def solve_local_image_pick(img_rgb, cfg=None):
    cfg = cfg or {}
    title_ratio = float(cfg.get("title_ratio", 0.24))
    cols = int(cfg.get("grid_cols", 3))
    rows = int(cfg.get("grid_rows", 2))
    min_margin = float(cfg.get("min_score_margin", 0.5))

    question = extract_question(img_rgb, title_ratio)
    if not question or len(question) < 2:
        return None, "OCR 未读到题目，请重新校准区域确保包含顶部文字"

    cells = _split_grid(img_rgb, cols, rows, title_ratio)
    prompts = [
        question,
        f"一张{question}的照片",
        f"{question}的图片",
    ]

    import torch

    model, processor = _get_clip()
    scored = []

    for cell_img, cx, cy in cells:
        if cell_img.size == 0:
            continue
        pil = Image.fromarray(cell_img)
        inputs = processor(text=prompts, images=pil, return_tensors="pt", padding=True)
        with torch.no_grad():
            logits = model(**inputs).logits_per_image
            score = float(logits.max().item())
        scored.append((score, cx, cy))

    if len(scored) < 2:
        return None, "未能切分图片格子，请重新校准区域"

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, x, y = scored[0]
    second_score = scored[1][0]

    if best_score - second_score < min_margin:
        return None, (
            f"题目「{question}」置信度不够(最高{best_score:.2f} vs 次高{second_score:.2f})，跳过避免乱点"
        )

    detail = f"题目={question} score={best_score:.2f} click=({x},{y})"
    return {"x": x, "y": y, "type": "image", "detail": detail}, None
