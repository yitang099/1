#!/usr/bin/env python3
"""Phase 4: rainbow api acts, notify endpoints, submit oracle. Use proxy if WAF blocked."""
import json, subprocess, sys, time

BASE = "https://xinhe001.lol/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
HDR = ["-H", "Accept-Language: zh-CN,zh;q=0.9", "-H", f"Referer: {BASE}/"]
DELAY = 6

RAINBOW_API_ACTS = [
    "search", "classlist", "siteinfo", "goodslist", "goodsdetails",
    "goodslistbycid", "getleftcount", "tools", "orders", "change", "clone",
    "pay", "token",
]

NOTIFY_PATHS = [
    "other/notify.php",
    "other/notify.php?act=epay",
    "other/notify.php?act=usdt",
    "other/notify.php?act=alipay",
    "other/epay_notify.php",
    "other/alipay_notify.php",
    "other/wxpay_notify.php",
]

SUBMIT_CASES = [
    ("no_type", "other/submit.php?orderid=1"),
    ("fake_alipay", "other/submit.php?orderid=1&type=alipay"),
    ("fake_usdt", "other/submit.php?orderid=1&type=usdt"),
]


def curl(url, method="GET", data=None, timeout=20):
    time.sleep(DELAY)
    cmd = ["curl", "-sS", "-m", str(timeout), "-w", "\n__HTTP__%{http_code}", "-A", UA] + HDR
    if method == "POST":
        cmd += ["-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded"]
        if data:
            cmd += ["-d", data]
    cmd.append(url)
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", "replace")
    except subprocess.CalledProcessError as e:
        out = e.output.decode("utf-8", "replace")
    if "__HTTP__" in out:
        body, _, code = out.rpartition("__HTTP__")
        return body.strip(), int(code)
    return out.strip(), 0


def main():
    hits = []

    print("=== rainbow api.php acts ===", flush=True)
    for act in RAINBOW_API_ACTS:
        if act == "search":
            for method, extra in [("GET", "id=1"), ("POST", "id=1")]:
                url = f"{BASE}/api.php?act={act}"
                body, code = curl(url, method, extra if method == "POST" else None)
                tag = f"api {act} {method}"
                print(f"  {tag} http={code} {body[:100]}", flush=True)
                if code == 200 and '"code":0' in body:
                    hits.append({"tag": tag, "body": body[:500]})
        elif act in ("goodslist", "goodsdetails", "getleftcount", "pay"):
            data = {"tid": "9", "cid": "1"} if act != "goodslist" else {}
            body, code = curl(f"{BASE}/api.php?act={act}", "POST", "&".join(f"{k}={v}" for k, v in data.items()))
            print(f"  api {act} POST http={code} {body[:100]}", flush=True)
            if code == 200 and body and "403" not in body and "500" not in body[:20]:
                hits.append({"tag": f"api {act}", "body": body[:500]})
        else:
            body, code = curl(f"{BASE}/api.php?act={act}")
            print(f"  api {act} http={code} {body[:100]}", flush=True)
            if code == 200 and body and body not in ('{"code":-5,"msg":"No Act!"}',) and "500" not in str(code):
                if '"code":0' in body or len(body) > 50:
                    hits.append({"tag": f"api {act}", "body": body[:500]})

    print("\n=== notify endpoints ===", flush=True)
    for p in NOTIFY_PATHS:
        body, code = curl(f"{BASE}/{p}")
        print(f"  {p} http={code} {body[:80]}", flush=True)
        if code == 200 and body and body not in ("error", "No Act", ""):
            hits.append({"tag": p, "body": body[:300]})

    print("\n=== submit oracle ===", flush=True)
    for name, p in SUBMIT_CASES:
        body, code = curl(f"{BASE}/{p}")
        print(f"  {name} http={code} {body[:120]}", flush=True)

    print("\n=== hidden SKU search ===", flush=True)
    body, code = curl(f"{BASE}/?mod=so&kw=美卡假绑")
    if "假绑" in body:
        hits.append({"tag": "hidden SKU", "body": "美卡假绑 search visible"})
        print("  [+] 美卡假绑 SKU found in search", flush=True)

    out = "/workspace/aaap-recon/xinhe_phase4_results.json"
    with open(out, "w") as f:
        json.dump({"hits": hits}, f, ensure_ascii=False, indent=2)
    print(f"\n[*] {len(hits)} hits -> {out}", flush=True)


if __name__ == "__main__":
    main()
