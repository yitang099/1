#!/usr/bin/env python3
"""Dump alipay.php headers/body without following redirects."""
import json, subprocess, re, time, urllib.parse
from pathlib import Path
QG,PW="C413ED6D","344F550A6F8B"; BASE="https://qq1.lol"
OUT=Path("/tmp/qq1_deep7")

def servers():
    d=json.loads(subprocess.check_output(["curl","-s",f"https://share.proxy.qg.net/query?key={QG}"],text=True,timeout=12))
    return [x["server"] for x in (d.get("data") or [])]

def pick():
    for s in servers():
        px=f"http://{QG}:{PW}@{s}"
        code=subprocess.run(["curl","-sk","--max-time","12","-x",px,"-o","/tmp/t.out","-w","%{http_code}",f"{BASE}/%61pi.php?act=siteinfo"],capture_output=True,text=True,timeout=15).stdout.strip()
        if code=="200" and b"sitename" in open("/tmp/t.out","rb").read():
            print("px",s); return px
    return None

px=pick()
jar=str(OUT/"ali.jar")
Path(jar).unlink(missing_ok=True)

def c(url, post=None, extra=None):
    cmd=["curl","-sk","--max-time","20","-x",px,"-b",jar,"-c",jar,"-A","Mozilla/5.0",
         "-H","Referer: https://qq1.lol/other/submit.php",
         "-D","-","-o","/tmp/ali_body.out","-w","\n__CODE:%{http_code}"]
    if extra: cmd=extra+cmd
    if post is not None:
        cmd += ["-X","POST","--data-binary",urllib.parse.urlencode(post),
                "-H","Content-Type: application/x-www-form-urlencoded"]
    cmd.append(url)
    out=subprocess.run(cmd,capture_output=True,text=True,timeout=25).stdout or ""
    body=open("/tmp/ali_body.out","rb").read()
    return out, body

# create order
c(BASE+"/")
buy_hdr, buy_body = c(BASE+"/?mod=buy&cid=4&tid=102")
buy=buy_body.decode("utf-8","replace")
csrf=re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy)
hs_m=re.search(r"var hashsalt=(.+);", buy)
print("csrf",bool(csrf),"hs",bool(hs_m))
hs=subprocess.run(["node","-e",f"var hashsalt={hs_m.group(1)}; console.log(hashsalt)"],capture_output=True,text=True,timeout=5).stdout.strip()
pay_hdr, pay_body=c(BASE+"/ajax.php?act=pay",{"tid":"102","num":"1","inputvalue":"alidump","csrf_token":csrf.group(1),"hashsalt":hs,"geetest_challenge":"1","geetest_validate":"1","geetest_seccode":"1|jordan"})
pay=pay_body.decode()
print("pay",pay[:200])
tn=re.search(r'"trade_no"\s*:\s*"(\d+)"', pay).group(1)
print("tn",tn)

# dump alipay without -L
for url in [f"{BASE}/other/alipay.php?trade_no={tn}", f"{BASE}/other/submit.php?type=alipay&orderid={tn}"]:
    print("====", url)
    hdr, body = c(url)
    print("HEADERS:", hdr[:800])
    print("BODY:", body[:1500])
    open(str(OUT/"alipay_dump_headers.txt"),"a").write(hdr+"\n\n")
    open(str(OUT/"alipay_dump_body.html"),"wb").write(body)
    # extract
    text=body.decode("utf-8","replace")
    print("locs", re.findall(r"location\.href\s*=\s*['\"]([^'\"]+)", text))
    print("urls", re.findall(r"https?://[^\s\"'<>]+", text)[:10])
    print("pid", re.findall(r"pid[=\"':\s]+([0-9]+)", text)[:5])
