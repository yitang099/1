"""可选视觉 API：帮第1步选图。无 API 时走词库/OCR 规则。"""
from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.request
from typing import Any

import cv2
import numpy as np


def _bgr_to_b64(bgr: np.ndarray) -> str:
    ok, buf = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        raise ValueError("encode image failed")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _parse_cell_index(text: str) -> int | None:
    m = re.search(r"[1-6]", text)
    if not m:
        return None
    return int(m.group()) - 1


def pick_step1_cell_via_api(
    grid_bgr: np.ndarray,
    keyword: str,
    cfg: dict,
) -> tuple[int | None, str]:
    """调用 OpenAI 兼容视觉 API，返回格子序号 0-5。"""
    api_key = (cfg.get("ai_api_key") or "").strip()
    base_url = (cfg.get("ai_base_url") or "https://api.openai.com/v1").rstrip("/")
    model = (cfg.get("ai_model") or "gpt-4o-mini").strip()
    if not api_key:
        return None, "未配置 API Key"

    img_b64 = _bgr_to_b64(grid_bgr)
    prompt = (
        f"这是验证码图片区，2行3列共6张图（从左到右、从上到下编号1-6）。"
        f"请选择最符合「{keyword}」的一张。只回复一个数字1到6，不要解释。"
    )
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ],
            }
        ],
        "max_tokens": 16,
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = str(data["choices"][0]["message"]["content"])
        idx = _parse_cell_index(text)
        if idx is None or idx < 0 or idx > 5:
            return None, f"AI 回复无法解析: {text[:40]}"
        return idx, f"AI 选第 {idx + 1} 格"
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="replace")[:120]
        except Exception:
            detail = str(e)
        return None, f"AI 请求失败: {detail}"
    except Exception as e:
        return None, f"AI 请求失败: {e}"


def ai_available(cfg: dict) -> bool:
    return bool((cfg.get("ai_api_key") or "").strip()) and bool(cfg.get("ai_enabled", False))
