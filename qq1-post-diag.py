#!/usr/bin/env python3
"""Diagnose whether POST body reaches qq1 api; try plain api.php; try user reg+login."""
import json,re,subprocess,time,urllib.parse,random,string
from pathlib import Path
OUT=Path("/tmp/qq1_deep7"); QG,PW="C413ED6D","344F550A6F8B"; BASE="https://qq1.lol"

def servers():
    raw=subprocess.check_output(["curl","-s",f"https://share.proxy.qg.net/query?key={QG}"],text=True,timeout=12)
    d=json.loads(raw)
    return [x["server"] for x in (d.get("data") or [])]

def pick():
    for srv in servers():
        px=f"http://{QG}:{PW}@{srv}"
        code=subprocess.run(["curl","-sk","--max-time","12","-x",px,"-o","/tmp/t.out","-w","%{http_code}",
                             f"{BASE}/%61pi.php?act=siteinfo"],capture_output=True,text=True,timeout=15).stdout.strip()
        if code=="200" and b"sitename" in open("/tmp/t.out","rb").read():
            print("px",srv); return px
    return None

def run(px, jar, url, post=None, extra=None):
    cmd=["curl","-sk","--max-time","16","-x",px,"-b",jar,"-c",jar,"-A","Mozilla/5.0",
         "-H","Referer: https://qq1.lol/","-H","X-Requested-With: XMLHttpRequest","-w","\n__HTTP:%{http_code}"]
    if extra: cmd += extra
    if post is not None:
        body=urllib.parse.urlencode(post) if isinstance(post,dict) else post
        cmd += ["-X","POST","--data-binary",body,"-H","Content-Type: application/x-www-form-urlencoded"]
    cmd.append(url)
    out=subprocess.run(cmd,capture_output=True,text=True,timeout=20).stdout or ""
    if "__HTTP:" not in out: return out.strip(),"000"
    b,c=out.rsplit("__HTTP:",1); return b.strip(),c.strip()

px=pick()
if not px: raise SystemExit("no px")
jar="/tmp/qq1_deep7/diag.jar"
Path(jar).unlink(missing_ok=True)

tests=[
 ("enc_POST_change", f"{BASE}/%61pi.php?act=change&id=25949&zt=1", {"key":"test"}),
 ("plain_POST_change", f"{BASE}/api.php?act=change&id=25949&zt=1", {"key":"test"}),
 ("enc_POST_tools", f"{BASE}/%61pi.php?act=tools", {"key":"test","limit":"1"}),
 ("plain_POST_tools", f"{BASE}/api.php?act=tools", {"key":"test","limit":"1"}),
 ("enc_GET_tools", f"{BASE}/%61pi.php?act=tools&key=test&limit=1", None),
 ("plain_GET_tools", f"{BASE}/api.php?act=tools&key=test&limit=1", None),
 ("httpbin_echo", "https://httpbin.org/post", {"key":"test","hello":"world"}),  # verify proxy POST works
]
for name,url,post in tests:
    b,c=run(px,jar,url,post)
    print(f"{name}: HTTP={c} {b[:200]}")
    time.sleep(0.5)

# user reg attempt with fake geetest
print("=== REG ===")
Path(jar).unlink(missing_ok=True)
run(px,jar,BASE+"/")
user="t"+"".join(random.choices(string.ascii_lowercase+string.digits,k=8))
pwd="Test"+"".join(random.choices(string.digits,k=6))+"!"
# get csrf from reg page
reg,c=run(px,jar,BASE+"/user/reg.php")
csrf=re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', reg or "")
print("reg page", c, "csrf", bool(csrf), "len", len(reg or ""))
if csrf:
    # try several reg field sets common in caihong
    for payload in [
        {"user":user,"pwd":pwd,"qq":"123456","code":"","csrf_token":csrf.group(1),
         "geetest_challenge":"1","geetest_validate":"1","geetest_seccode":"1|jordan"},
        {"user":user+"2","pwd":pwd,"email":"a@b.c","qq":"123456","csrf_token":csrf.group(1),
         "geetest_challenge":"1","geetest_validate":"1","geetest_seccode":"1|jordan"},
    ]:
        b,c=run(px,jar,BASE+"/ajax.php?act=reg", payload)
        print("reg ajax", c, (b or "")[:200])
        if b and ("成功" in b or '"code":0' in b or '"code":1' in b):
            print("REG_OK", payload["user"], pwd)
            # login
            b2,c2=run(px,jar,BASE+"/ajax.php?act=login", {"user":payload["user"],"pwd":pwd,"csrf_token":csrf.group(1),
                "geetest_challenge":"1","geetest_validate":"1","geetest_seccode":"1|jordan"})
            print("login", c2, (b2 or "")[:200])
            # try change with session
            b3,c3=run(px,jar,f"{BASE}/%61pi.php?act=change&id=25949&zt=1")
            print("change_as_user", c3, (b3 or "")[:200])
            b4,c4=run(px,jar,f"{BASE}/%61pi.php?act=orders&limit=1&tid=102")
            print("orders_as_user", c4, (b4 or "")[:200])
            break
        time.sleep(0.5)
print("DONE")
