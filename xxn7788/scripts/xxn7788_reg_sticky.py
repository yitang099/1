#!/usr/bin/env python3
"""xxn7788 Geetest register with sticky Qingguo proxy passed to 2Captcha."""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

import requests

JP, JP_PASS = "124.248.67.170", "UzHlZQDUy7XP"
BASE = "https://xxn7788.top/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
CK = "/tmp/xxn_login5.ck"
OUT = Path("/data/automation/results/xxn7788.top/login_2captcha")
OUT.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    print(msg, flush=True)
    open(OUT / "login5.log", "a").write(msg + "\n")


def jp(cmd: str, t: int = 180) -> str:
    r = subprocess.run(
        [
            "sshpass",
            "-p",
            JP_PASS,
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "ConnectTimeout=20",
            f"root@{JP}",
            cmd,
        ],
        capture_output=True,
        timeout=t,
    )
    return (r.stdout or b"").decode("utf-8", "replace")


def main() -> int:
    key = None
    for line in open("/data/recon/cookie_tool/config/2captcha.env"):
        if line.startswith("TWOCAPTCHA_API_KEY="):
            key = line.split("=", 1)[1].strip()
    assert key

    subprocess.run(["/data/automation/bin/qg-proxy-fetch.sh"], capture_output=True, timeout=30)
    env = open("/data/config/proxy.env").read()
    m = re.search(r"PROXY_URL=(\S+)", env)
    assert m, env
    proxy = m.group(1).strip().strip('"')
    log(f"STICKY={proxy}")
    subprocess.run(
        [
            "sshpass",
            "-p",
            JP_PASS,
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            f"root@{JP}",
            "mkdir -p /data/config; cat > /data/config/proxy.env",
        ],
        input=env.encode(),
        capture_output=True,
        timeout=25,
    )

    boot = jp(
        f"""
PROXY_URL='{proxy}'; export PROXY_URL
UA='{UA}'; BASE='{BASE}'; CK={CK}
rm -f "$CK"
curl -sk -x "$PROXY_URL" -c "$CK" -b "$CK" --max-time 25 -A "$UA" "$BASE/user/reg.php" -o /tmp/xxn_reg.html -w "REG=%{{http_code}}\\n"
python3 - <<'P'
import re, subprocess
h = open('/tmp/xxn_reg.html', encoding='utf-8', errors='ignore').read()
csrf = re.search(r'var\\s+csrf_token\\s*=\\s*"([^"]+)"', h)
hs = re.search(r'var\\s+hashsalt\\s*=\\s*(.+?);', h, re.S)
print('CSRF=' + (csrf.group(1) if csrf else ''))
assert hs, 'no hashsalt'
open('/tmp/xxn_hs.js', 'w').write('console.log(' + hs.group(1) + ')\\n')
print('HS=' + subprocess.check_output(['node', '/tmp/xxn_hs.js'], text=True).strip().splitlines()[-1])
P
curl -sk -x "$PROXY_URL" -b "$CK" -c "$CK" --max-time 15 -A "$UA" -e "$BASE/user/reg.php" \
  -H 'X-Requested-With: XMLHttpRequest' "$BASE/ajax.php?act=captcha"
echo
"""
    )
    (OUT / "boot5.txt").write_text(boot)
    log(boot[:600])
    csrf = re.search(r"CSRF=([a-f0-9]+)", boot)
    hs = re.search(r"HS=([a-f0-9]+)", boot)
    assert csrf and hs, "missing csrf/hs"
    csrf_v, hs_v = csrf.group(1), hs.group(1)
    cap = None
    for line in boot.splitlines():
        line = line.strip()
        if line.startswith("{") and "gt" in line:
            cap = json.loads(line)
    assert cap and cap.get("gt"), cap
    log(f"gt={cap['gt']} ch={cap['challenge']} hs={hs_v}")

    pm = re.match(r"http://([^:]+):([^@]+)@([^:/]+):(\d+)", proxy)
    assert pm, proxy
    proxy_param = f"{pm.group(1)}:{pm.group(2)}@{pm.group(3)}:{pm.group(4)}"
    params = {
        "key": key,
        "method": "geetest",
        "gt": cap["gt"],
        "challenge": cap["challenge"],
        "pageurl": f"{BASE}/user/reg.php",
        "json": 1,
        "proxy": proxy_param,
        "proxytype": "HTTP",
    }
    r = requests.get("https://2captcha.com/in.php", params=params, timeout=30)
    log(f"CREATE={r.text}")
    j = r.json()
    assert j.get("status") == 1, j
    tid = j["request"]
    geetest = None
    for i in range(36):
        time.sleep(5)
        rr = requests.get(
            "https://2captcha.com/res.php",
            params={"key": key, "action": "get", "id": tid, "json": 1},
            timeout=30,
        )
        log(f"RES[{i}]={rr.text[:220]}")
        jj = rr.json()
        if jj.get("status") == 1:
            req = jj["request"]
            geetest = json.loads(req) if isinstance(req, str) else req
            break
        if "ERROR" in str(jj.get("request")):
            break
    assert geetest, "solve failed"
    log(f"SOL={geetest}")

    user = f"xxn{int(time.time()) % 10000000}"
    pwd = "Xxn7788!aB"
    payload = {
        "user": user,
        "pwd": pwd,
        "qq": "123456789",
        "hashsalt": hs_v,
        "csrf_token": csrf_v,
        "geetest_challenge": geetest.get("geetest_challenge") or geetest.get("challenge", ""),
        "geetest_validate": geetest.get("geetest_validate") or geetest.get("validate", ""),
        "geetest_seccode": geetest.get("geetest_seccode")
        or geetest.get("seccode")
        or ((geetest.get("geetest_validate") or "") + "|jordan"),
    }
    open("/tmp/xxn_reg_payload.json", "w").write(json.dumps(payload, ensure_ascii=False))
    subprocess.run(
        [
            "sshpass",
            "-p",
            JP_PASS,
            "scp",
            "-o",
            "StrictHostKeyChecking=no",
            "/tmp/xxn_reg_payload.json",
            f"root@{JP}:/tmp/xxn_reg_payload.json",
        ],
        capture_output=True,
        timeout=30,
    )

    out = jp(
        f"""
PROXY_URL='{proxy}'; export PROXY_URL
UA='{UA}'; BASE='{BASE}'; CK={CK}
python3 -c "import json,urllib.parse;p=json.load(open('/tmp/xxn_reg_payload.json'));open('/tmp/xxn_reg_body.txt','w').write(urllib.parse.urlencode(p))"
echo REG=$(curl -sk -x "$PROXY_URL" -b "$CK" -c "$CK" --max-time 25 -A "$UA" -e "$BASE/user/reg.php" \
  -H 'X-Requested-With: XMLHttpRequest' -H 'Content-Type: application/x-www-form-urlencoded' \
  -X POST --data-binary @/tmp/xxn_reg_body.txt "$BASE/user/ajax.php?act=reguser")
echo CHECK=$(curl -sk -x "$PROXY_URL" -b "$CK" -c "$CK" --max-time 15 -A "$UA" -H 'X-Requested-With: XMLHttpRequest' "$BASE/ajax.php?act=checklogin")
echo CREDS={user}:{pwd}
"""
    )
    (OUT / "login5.txt").write_text(out)
    log(out)
    open(OUT / "creds.txt", "w").write(f"{user}:{pwd}\n")
    if '"code":1' in out:
        log("REG_OK")
        (OUT / "cookies.txt").write_text(jp(f"cat {CK}"))
        return 0
    log("REG_FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
