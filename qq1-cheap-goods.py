#!/usr/bin/env python3
import json
import subprocess

QG, PW = "C413ED6D", "344F550A6F8B"
d = json.loads(subprocess.check_output(
    ["curl", "-s", f"https://share.proxy.qg.net/query?key={QG}"], text=True))
px = None
for x in d.get("data") or []:
    cand = f"http://{QG}:{PW}@{x['server']}"
    code = subprocess.run(
        ["curl", "-sk", "--max-time", "10", "-x", cand, "-o", "/tmp/g.out",
         "-w", "%{http_code}", "https://qq1.lol/%61pi.php?act=goodslist"],
        capture_output=True, text=True).stdout.strip()
    if code == "200":
        px = cand
        break
if not px:
    d = json.loads(subprocess.check_output(
        ["curl", "-s", f"https://share.proxy.qg.net/get?key={QG}&num=1&area=440000"], text=True))
    x = d["data"][0]
    px = f"http://{QG}:{PW}@{x['server']}"
    subprocess.run(["curl", "-sk", "--max-time", "10", "-x", px, "-o", "/tmp/g.out",
                    "https://qq1.lol/%61pi.php?act=goodslist"])

j = json.loads(open("/tmp/g.out", encoding="utf-8", errors="replace").read())
items = j.get("data") or (j if isinstance(j, list) else [])
priced = []
for it in items:
    try:
        price = float(it.get("price") or 99999)
    except Exception:
        continue
    priced.append((price, str(it.get("tid")), str(it.get("name", ""))[:50],
                   it.get("close"), it.get("stock"), it.get("active")))
priced.sort()
print("total", len(priced))
print("cheapest 30:")
for row in priced[:30]:
    print(row)
print("price<=1:", [r for r in priced if r[0] <= 1][:30])
print("price<=10:", [r for r in priced if r[0] <= 10][:30])
