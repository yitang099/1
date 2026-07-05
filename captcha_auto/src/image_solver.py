import base64
import io
import json
import re

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
    pairs = re.findall(r"(\d+)\s*[,，]\s*(\d+)", str(text))
    return [(int(x), int(y)) for x, y in pairs]


def call_tuling(img_rgb, api_cfg):
    url = api_cfg.get("url", "http://www.tulingtech.xyz/tuling/predict")
    payload = {
        "username": api_cfg["username"],
        "password": api_cfg["password"],
    }

    # 图灵新版用 ID + b64，旧版用 typeid + image
    if api_cfg.get("model_id"):
        payload["ID"] = str(api_cfg["model_id"])
        payload["b64"] = _image_to_b64(img_rgb)
    else:
        payload["typeid"] = int(api_cfg.get("typeid", 19))
        payload["image"] = _image_to_b64(img_rgb)

    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, dict):
        if data.get("success") is False:
            raise RuntimeError(data.get("message") or data)
        if "data" in data and isinstance(data["data"], dict):
            result = data["data"].get("result") or data["data"]
        else:
            result = data.get("result") or data.get("data") or data
    else:
        result = data

    if isinstance(result, dict):
        text = result.get("result") or json.dumps(result, ensure_ascii=False)
    else:
        text = str(result)

    coords = _parse_coords(text)
    if not coords:
        raise RuntimeError(f"打码平台未返回坐标: {text}")
    return coords, text


def solve_image_pick(img_rgb, api_cfg):
    coords, raw = call_tuling(img_rgb, api_cfg)
    x, y = coords[0]
    return {"x": x, "y": y, "type": "image", "detail": raw}, None
