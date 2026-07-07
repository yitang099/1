"""第1步本地识图：颜色/纹理启发式，无需 API。"""
from __future__ import annotations

import cv2
import numpy as np

# 常见验证码物体 → HSV 颜色区间 (lo, hi)
_COLOR_HINTS: dict[str, list[tuple[tuple[int, int, int], tuple[int, int, int]]]] = {
  "柠檬": [((18, 80, 80), (40, 255, 255))],
  "香蕉": [((18, 70, 80), (35, 255, 255))],
  "橙子": [((5, 100, 100), (20, 255, 255))],
  "草莓": [((0, 80, 80), (10, 255, 255))],
  "苹果": [((0, 80, 60), (10, 255, 255)), ((35, 40, 40), (85, 255, 200))],
  "葡萄": [((120, 50, 40), (150, 255, 200))],
  "西瓜": [((35, 50, 50), (85, 255, 255)), ((0, 80, 60), (10, 255, 255))],
  "胡萝卜": [((5, 100, 100), (18, 255, 255))],
  "茄子": [((120, 40, 30), (150, 255, 180))],
  "玉米": [((18, 60, 80), (35, 255, 255))],
  "蘑菇": [((0, 0, 180), (180, 40, 255)), ((10, 30, 80), (25, 180, 200))],
  "兔子": [((35, 30, 80), (90, 180, 255)), ((10, 30, 60), (25, 180, 220))],
  "猫": [((0, 0, 40), (180, 255, 200))],
  "狗": [((10, 30, 40), (25, 200, 220)), ((0, 0, 30), (180, 80, 180))],
  "鸟": [((90, 50, 50), (130, 255, 255)), ((0, 0, 180), (180, 50, 255))],
  "鱼": [((90, 50, 50), (130, 255, 255)), ((100, 80, 80), (130, 255, 255))],
  "汽车": [((0, 0, 20), (180, 80, 200))],
  "自行车": [((0, 0, 20), (180, 100, 220))],
  "花": [((0, 60, 60), (180, 255, 255))],
  "树": [((35, 40, 40), (85, 255, 200))],
  "草": [((35, 50, 50), (85, 255, 200))],
  "云": [((0, 0, 200), (180, 40, 255))],
  "太阳": [((15, 100, 100), (35, 255, 255))],
  "月亮": [((0, 0, 180), (180, 50, 255))],
  "星星": [((15, 80, 120), (40, 255, 255))],
}


def _color_ratio(cell_bgr: np.ndarray, ranges: list[tuple[tuple[int, int, int], tuple[int, int, int]]]) -> float:
  hsv = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2HSV)
  total = cell_bgr.shape[0] * cell_bgr.shape[1]
  if total <= 0:
    return 0.0
  mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
  for lo, hi in ranges:
    mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lo, hi))
  return float(cv2.countNonZero(mask)) / total


def _texture_score(cell_bgr: np.ndarray) -> float:
  gray = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2GRAY)
  return float(cv2.Laplacian(gray, cv2.CV_64F).var()) / 1000.0


def score_cell_for_keyword(cell_bgr: np.ndarray, keyword: str) -> float:
  kw = keyword.strip()
  if not kw:
    return 0.0

  score = 0.0
  for key, ranges in _COLOR_HINTS.items():
    if key in kw or kw in key:
      score = max(score, _color_ratio(cell_bgr, ranges) * 3.5)

  # 单字颜色线索
  if "黄" in kw or "金" in kw:
    score = max(score, _color_ratio(cell_bgr, [((18, 80, 80), (40, 255, 255))]) * 3.0)
  if "红" in kw:
    score = max(score, _color_ratio(cell_bgr, [((0, 80, 80), (10, 255, 255))]) * 3.0)
  if "绿" in kw or "青" in kw:
    score = max(score, _color_ratio(cell_bgr, [((35, 50, 50), (85, 255, 200))]) * 3.0)
  if "蓝" in kw:
    score = max(score, _color_ratio(cell_bgr, [((90, 50, 50), (130, 255, 255))]) * 3.0)
  if "白" in kw:
    score = max(score, _color_ratio(cell_bgr, [((0, 0, 200), (180, 40, 255))]) * 2.5)
  if "黑" in kw:
    score = max(score, _color_ratio(cell_bgr, [((0, 0, 0), (180, 255, 80))]) * 2.5)

  score += min(_texture_score(cell_bgr), 1.5) * 0.15
  return score


def rank_cells_local(keyword: str, cells: list[np.ndarray], *, top_n: int = 3) -> list[tuple[int, float]]:
  ranked = [(i, score_cell_for_keyword(cell, keyword)) for i, cell in enumerate(cells)]
  ranked.sort(key=lambda x: x[1], reverse=True)
  return [(i, s) for i, s in ranked[:top_n] if s > 0.08]
