#!/usr/bin/env python3
"""Solve Geetest v3 via 2Captcha / 2验证码 API."""
from __future__ import annotations

import json
import os
import time
from typing import Any

import requests

DEFAULT_KEY_ENV = "TWOCAPTCHA_API_KEY"
API_IN = "https://2captcha.com/in.php"
API_RES = "https://2captcha.com/res.php"

CONFIG_PATHS = (
    "/data/tools/faka/cookie/2captcha.env",
    "/data/recon/cookie_tool/config/2captcha.env",
)


def get_api_key(explicit: str | None = None) -> str:
    key = explicit or os.environ.get(DEFAULT_KEY_ENV, "")
    if not key:
        for cfg in CONFIG_PATHS:
            if not os.path.isfile(cfg):
                continue
            for line in open(cfg, encoding="utf-8"):
                line = line.strip()
                if line.startswith("TWOCAPTCHA_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"\'')
                    break
            if key:
                break
    if not key:
        raise RuntimeError("missing 2captcha API key (TWOCAPTCHA_API_KEY or config file)")
    return key


def solve_geetest_v3(
    *,
    gt: str,
    challenge: str,
    pageurl: str,
    api_server: str | None = None,
    api_key: str | None = None,
    poll_interval: float = 5.0,
    timeout: float = 120.0,
) -> dict[str, str]:
    key = get_api_key(api_key)
    params: dict[str, Any] = {
        "key": key,
        "method": "geetest",
        "gt": gt,
        "challenge": challenge,
        "pageurl": pageurl,
        "json": 1,
    }
    if api_server:
        params["api_server"] = api_server
    r = requests.get(API_IN, params=params, timeout=30)
    r.raise_for_status()
    j = r.json()
    if j.get("status") != 1:
        raise RuntimeError(f"2captcha submit failed: {j}")
    task_id = j["request"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(poll_interval)
        rr = requests.get(
            API_RES,
            params={"key": key, "action": "get", "id": task_id, "json": 1},
            timeout=30,
        )
        rr.raise_for_status()
        rj = rr.json()
        if rj.get("status") == 1:
            req = rj["request"]
            sol = json.loads(req) if isinstance(req, str) else req
            return {
                "geetest_challenge": sol.get("geetest_challenge") or sol.get("challenge", ""),
                "geetest_validate": sol.get("geetest_validate") or sol.get("validate", ""),
                "geetest_seccode": sol.get("geetest_seccode") or sol.get("seccode", ""),
            }
        if rj.get("request") in ("ERROR_CAPTCHA_UNSOLVABLE", "ERROR_WRONG_CAPTCHA_ID"):
            raise RuntimeError(rj)
    raise TimeoutError(f"2captcha timeout task={task_id}")
