"""第1步关键词识别：多区域 OCR + 模糊提取。"""
from __future__ import annotations

import re

from slider_solver.screen_match import Region, grab_region
from verify_auto.ocr_util import ocr_lines, ocr_text, preprocess_for_ocr


def extract_keyword(text: str) -> str:
  t = text.replace("\n", " ").strip()
  if not t:
    return ""

  patterns = (
    r"[''『「\"“]([^''』」\"”]+)[''』」\"”]",
    r"描述的图片[：:\s]*[''\"“]?([^''\"'\s，,。．]+)",
    r"最符合[^'']*[''『「\"“]([^''』」\"”]+)[''』」\"”]",
    r"图片[：:\s]*[''\"“]?([\u4e00-\u9fffA-Za-z0-9]{1,8})",
    r"[：:]\s*[''\"“]?([\u4e00-\u9fff]{1,6})[''\"”]?",
    r"(?:选择|点击|找出)[^。]*?([\u4e00-\u9fff]{2,6})",
  )
  for pat in patterns:
    m = re.search(pat, t)
    if m:
      kw = m.group(1).strip(" '\"“”‘’，,。．:：")
      if kw and kw not in ("的", "图片", "描述", "选择", "最符合", "一张", "元素"):
        return kw

  # 锚点行里最后一个短中文词
  if any(k in t for k in ("最符合", "描述的图片", "选择最符合")):
    chunks = re.findall(r"[\u4e00-\u9fff]{2,6}", t)
    for word in reversed(chunks):
      if word not in ("选择最符合", "描述的图片", "最符合描述", "选择", "图片", "描述", "符合"):
        return word
  return ""


def _ocr_variants(bgr) -> list[str]:
  texts: list[str] = []
  if bgr is None or bgr.size == 0:
    return texts
  texts.append(ocr_text(bgr))
  lines = ocr_lines(bgr)
  if lines:
    texts.append(" ".join(line.text for line in lines))
    for line in lines:
      if any(k in line.text for k in ("最符合", "描述", "图片", "选择")):
        texts.insert(0, line.text)
  sharp = preprocess_for_ocr(bgr)
  if sharp is not None and sharp.size:
    texts.append(ocr_text(sharp))
  return [t for t in texts if t.strip()]


def extract_keyword_from_region(region: Region | None) -> tuple[str, str]:
  if not region:
    return "", ""
  texts = _ocr_variants(grab_region(region))
  debug = texts[0][:120] if texts else ""
  for text in texts:
    kw = extract_keyword(text)
    if kw:
      return kw, text[:120]
  return "", debug


def extract_keyword_robust(
  *,
  step1_prompt: Region | None = None,
  search: Region | None = None,
  grid: Region | None = None,
) -> tuple[str, str]:
  """从多个区域尝试读关键词，返回 (关键词, 调试文本)。"""
  regions: list[Region] = []
  if search:
    regions.append(search)
  if step1_prompt:
    regions.append(step1_prompt)
    pr = step1_prompt
    regions.append(
      Region(max(0, pr.left - 30), max(0, pr.top - 12), pr.width + 160, pr.height + 24)
    )
  if grid and step1_prompt:
    # 提示行偶尔与网格上沿重叠
    g = grid
    regions.append(Region(g.left, max(0, g.top - 48), g.width, 48))

  seen: set[str] = set()
  last_debug = ""
  for region in regions:
    key = (region.left, region.top, region.width, region.height)
    if key in seen:
      continue
    seen.add(key)
    kw, debug = extract_keyword_from_region(region)
    if debug:
      last_debug = debug
    if kw:
      return kw, debug
  return "", last_debug
