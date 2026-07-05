import base64
import io
import json
import os
import re
import time

import numpy as np
import requests
from PIL import Image


def _image_to_b64(img_rgb):
    pil = Image.fromarray(img_rgb)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _parse_coords(text):
    if not text:
        return []
    s = str(text)
    if re.fullmatch(r"[1-6]", s.strip()):
        return [int(s.strip())]
    pairs = re.findall(r"(\d+)\s*[,，|]\s*(\d+)", s)
    return [(int(x), int(y)) for x, y in pairs]


def _normalize_xy(x, y, w, h):
    if w <= 0 or h <= 0:
        return x, y
    if x <= 1.0 and y <= 1.0:
        return int(x * w), int(y * h)
    if x <= 1000 and y <= 1000 and (x > w or y > h):
        return int(x * w / 1000), int(y * h / 1000)
    return int(x), int(y)


def _cell_index_to_xy(index, w, h, cols=3, rows=2, title_ratio=0.22):
  # index 1-6, left-to-right, top-to-bottom
    idx = max(1, min(6, int(index))) - 1
    row, col = divmod(idx, cols)
    body_top = int(h * title_ratio)
    body_h = h - body_top
    cell_w = w / cols
    cell_h = body_h / rows
    x = int((col + 0.5) * cell_w)
    y = int(body_top + (row + 0.5) * cell_h)
    return x, y


def _validate_xy(x, y, w, h, margin=5):
    return margin <= x <= w - margin and margin <= y <= h - margin


def _save_debug(img_rgb, tag, debug_dir):
    if not debug_dir:
        return
    os.makedirs(debug_dir, exist_ok=True)
    path = os.path.join(debug_dir, f"{tag}_{int(time.time())}.png")
    Image.fromarray(img_rgb).save(path)


def _call_api(img_rgb, api_cfg, typeid=None, model_id=None, remark=None):
    url = api_cfg.get("url", "http://www.tulingtech.xyz/tuling/predict")
    payload = {
        "username": api_cfg["username"],
        "password": api_cfg["password"],
    }
    mid = model_id if model_id is not None else api_cfg.get("model_id")
    tid = typeid if typeid is not None else api_cfg.get("typeid", 19)

    if mid:
        payload["ID"] = str(mid)
        payload["b64"] = _image_to_b64(img_rgb)
    else:
        payload["typeid"] = int(tid)
        payload["image"] = _image_to_b64(img_rgb)

    if remark:
        payload["remark"] = remark
        payload["content"] = remark
        payload["title"] = remark

    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, dict) and data.get("success") is False:
        raise RuntimeError(data.get("message") or str(data))

    result = data
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], dict):
            result = data["data"].get("result") or data["data"]
        else:
            result = data.get("result") or data.get("data") or data

    if isinstance(result, dict):
        text = result.get("result") or json.dumps(result, ensure_ascii=False)
    else:
        text = str(result)
    return text


def extract_remark(img_rgb, api_cfg):
    manual = api_cfg.get("remark", "").strip()
    if manual:
        return manual

    h, w = img_rgb.shape[:2]
    title = img_rgb[: max(20, int(h * 0.24)), :]
    ocr_typeid = int(api_cfg.get("ocr_typeid", 32))
    try:
        text = _call_api(title, api_cfg, typeid=ocr_typeid, model_id="")
        m = re.search(r"[「『\"']([^」』\"']+)[」』\"']", text)
        if m:
            return m.group(1).strip()
        m = re.search(r"[:：]\s*(.+)$", text.replace("\n", ""))
        if m:
            return m.group(1).strip().strip("'\"")
    except Exception:
        pass
    return ""


def call_tuling(img_rgb, api_cfg):
    if not api_cfg.get("model_id") and not api_cfg.get("allow_generic_typeid"):
        raise RuntimeError(
            "选图验证码必须填写 api.model_id（图灵后台→腾讯选图/语义点选模型ID），"
            "否则坐标是乱的。动态点选用 F10，不要用 F9。"
        )

    remark = extract_remark(img_rgb, api_cfg)
    text = _call_api(img_rgb, api_cfg, remark=remark or None)
    parsed = _parse_coords(text)
    if not parsed:
        raise RuntimeError(f"打码平台未返回坐标: {text} (remark={remark})")
    return parsed, text, remark


def solve_image_pick(img_rgb, api_cfg):
    h, w = img_rgb.shape[:2]
    coords, raw, remark = call_tuling(img_rgb, api_cfg)

    if len(coords) == 1 and isinstance(coords[0], int):
        x, y = _cell_index_to_xy(coords[0], w, h)
    else:
        x, y = coords[0]
        x, y = _normalize_xy(x, y, w, h)

    if not _validate_xy(x, y, w, h):
        raise RuntimeError(f"坐标超出范围: ({x},{y}) 图大小({w}x{h}) 原始返回: {raw}")

    debug_dir = api_cfg.get("debug_dir", "")
    _save_debug(img_rgb, "image_pick", debug_dir)

    detail = f"remark={remark} raw={raw} click=({x},{y})"
    return {"x": x, "y": y, "type": "image", "detail": detail}, None
