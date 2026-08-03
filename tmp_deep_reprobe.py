#!/usr/bin/env python3
import os,re,json,subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
PROXY=os.environ['PROXY']
hosts=[h.strip() for h in Path('/data/qq_hunt/round3/reprobe_focus.txt').read_text().splitlines() if h.strip()]
OUT=Path('/data/qq_hunt/round3/exhaust_probe')
REJECT=re.compile(r'(域名已过期|DNSPod|卡盾|Facebook|Instagram|小红书|苹果id|Apple ID|WhatsApp|飞机号|海外账号|博彩|威尼斯|棋牌|casino|1xbet|Non-compliance|AI账号)',re.I)

def curl(url,t=15):
    try:
        p=subprocess.run(['curl','-sL','-A','Mozilla/5.0','--max-time',str(t),'-x',PROXY,'-k','--connect-timeout','6',url],capture_output=True,timeout=t+4)
        return p.stdout.decode('utf-8','ignore')
    except: return ''

def classify(body):
    if re.search(r'易发卡|ykfaka|YKFAKA',body,re.I): return 'YKFAKA易发卡'
    if re.search(r'异次元',body): return '异次元发卡'
    if re.search(r'独角',body): return '独角数卡'
    if re.search(r'title="商品库存">\d+个',body): return '卡网列表模板(通用自动发卡)'
    if re.search(r'靓号',body): return '靓号网/选号站'
    return '未识别模板'

def probe(host):
    best=None
    for url in [f'https://{host}/shop/', f'https://{host}/', f'http://{host}/shop/', f'http://{host}/']:
        body=curl(url)
        if len(body)<400: continue
        title_m=re.search(r'<title[^>]*>(.*?)</title>',body,re.I|re.S)
        title=re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',title_m.group(1) if title_m else '')).strip()[:140]
        if REJECT.search(title) and not re.search(r'QQ|企鹅', title):
            continue
        strong=bool(re.search(r'QQ|企鹅|扣扣|qq号|QQ号|卖Q|号商', body+title))
        sales=sum(int(x) for x in re.findall(r'(?:已售|销量)[^\d]{0,8}(\d+)',body))
        stock=sum(int(x) for x in re.findall(r'title="商品库存">(\d+)个',body))
        sys=classify(body)
        row={'host':host,'url':url,'title':title,'strong_qq':strong,'sales':sales,'stock':stock,'sys':sys,'len':len(body)}
        if strong and (stock>0 or sales>0 or sys.startswith(('YKFAKA','卡网','异次元','独角')) or '/shop' in url):
            return row
        if (stock>0 or sys.startswith(('YKFAKA','卡网'))) and (strong or re.search(r'qq|faka|hao',host,re.I)):
            return row
        if best is None or (strong and not best.get('strong_qq')):
            best=row
    return best or {'host':host,'url':'','title':'','strong_qq':False,'sales':0,'stock':0,'sys':'dead','len':0}

print('probing',len(hosts), PROXY, flush=True)
rows=[]
with ThreadPoolExecutor(max_workers=12) as ex:
    futs={ex.submit(probe,h):h for h in hosts}
    for i,fut in enumerate(as_completed(futs),1):
        r=fut.result(); rows.append(r)
        mark='QQ' if r.get('strong_qq') or (r.get('stock',0)>0 and r.get('sys','').startswith('卡网')) else ('hit' if r.get('len',0)>500 else 'dead')
        print(f"{i}/{len(hosts)} {mark} {r['host']} sales={r.get('sales')} stock={r.get('stock')} {r.get('sys')} {r.get('title','')[:50]}", flush=True)

alive=[r for r in rows if r.get('sys')!='dead' and r.get('len',0)>400 and (
    r.get('strong_qq') or (r.get('stock',0)>0 and re.search(r'qq|faka|hao', r['host'], re.I)) or
    (r.get('sys','').startswith('YKFAKA') and r.get('strong_qq'))
)]
# filter reject titles
alive=[r for r in alive if not (REJECT.search(r.get('title') or '') and not re.search(r'QQ|企鹅', r.get('title') or ''))]
(OUT/'reprobe_results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'reprobe_alive.json').write_text(json.dumps(alive,ensure_ascii=False,indent=2),encoding='utf-8')
print('ALIVE',len(alive),'/',len(rows),flush=True)
for r in sorted(alive, key=lambda x:(-x.get('sales',0),-x.get('stock',0))):
    print('+',r['host'],r['sales'],r['stock'],r['sys'],r['url'],r['title'][:55])
