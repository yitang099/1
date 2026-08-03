#!/usr/bin/env python3
import os,re,json,subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
PROXY=os.environ['PROXY']
hosts=[h.strip() for h in Path('/data/qq_hunt/round3/hot_probe.txt').read_text().splitlines() if h.strip()]
OUT=Path('/data/qq_hunt/round3/exhaust_probe')

def curl(url,t=16):
    try:
        p=subprocess.run(['curl','-sL','-A','Mozilla/5.0','--max-time',str(t),'-x',PROXY,'-k','--connect-timeout','6',url],capture_output=True,timeout=t+4)
        return p.stdout.decode('utf-8','ignore')
    except: return ''

def probe(host):
    urls=[f'https://{host}/', f'https://{host}/shop/', f'http://{host}/', f'http://{host}/shop/', f'https://{host}/index.php']
    best=None
    for url in urls:
        b=curl(url)
        if len(b)<400: continue
        title=re.search(r'<title[^>]*>(.*?)</title>',b,re.I|re.S)
        title=re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',title.group(1) if title else '')).strip()[:120]
        if re.search(r'域名已过期|DNSPod|404 Not Found|页面未找到', title) and not re.search(r'QQ|太白', title):
            continue
        strong=bool(re.search(r'QQ|企鹅|扣扣|一手出QQ|卖Q|QQ号', b+title))
        sales=sum(int(x) for x in re.findall(r'(?:已售|销量)[^\d]{0,8}(\d+)',b))
        stock=sum(int(x) for x in re.findall(r'title="商品库存">(\d+)个',b))
        # ykfaka item stock in table
        if not stock:
            # try count stock numbers near QQ items
            pass
        sys='未识别模板'
        if re.search(r'易发卡|ykfaka|YKFAKA',b,re.I): sys='YKFAKA易发卡'
        elif re.search(r'异次元|acg\.API|commoditys',b): sys='异次元发卡'
        elif re.search(r'title="商品库存">\d+个',b): sys='卡网列表模板(通用自动发卡)'
        elif re.search(r'独角',b): sys='独角数卡'
        items=re.findall(r'(?:Trade|Item)/\d+\.html\">\s*([^<]{4,70})',b)
        items+=re.findall(r'一手出QQ[^<]{0,40}|QQ注册卡[^<]{0,40}|月卡[^<]{0,30}',b)
        items=[re.sub(r'\s+',' ',i).strip() for i in items][:12]
        row={'host':host,'url':url,'title':title,'strong_qq':strong,'sales':sales,'stock':stock,'sys':sys,'items':items,'len':len(b)}
        if strong:
            return row
        if best is None: best=row
    return best or {'host':host,'url':'','title':'','strong_qq':False,'sales':0,'stock':0,'sys':'dead','items':[],'len':0}

print('hot probe',len(hosts),PROXY,flush=True)
rows=[]
with ThreadPoolExecutor(max_workers=10) as ex:
    futs={ex.submit(probe,h):h for h in hosts}
    for i,fut in enumerate(as_completed(futs),1):
        r=fut.result(); rows.append(r)
        mark='QQ' if r.get('strong_qq') else ('hit' if r.get('len',0)>500 else 'dead')
        print(f"{i}/{len(hosts)} {mark} {r['host']} {r.get('sys')} stock={r.get('stock')} {r.get('title','')[:45]} items={r.get('items',[])[:2]}", flush=True)

alive=[r for r in rows if r.get('strong_qq') and r.get('sys')!='dead']
(OUT/'hot_alive.json').write_text(json.dumps(alive,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'hot_all.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('ALIVE',len(alive),flush=True)
for r in alive:
    print('+',r['host'],r['sys'],r['url'],r['title'][:50], r.get('items',[])[:3])
