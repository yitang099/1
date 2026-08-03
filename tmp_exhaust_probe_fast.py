#!/usr/bin/env python3
import os,re,json,subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROXY=os.environ.get('PROXY','')
HOSTS_FILE=Path(os.environ.get('HOSTS_FILE','/data/qq_hunt/round3/exhaust_hosts.txt'))
OUT=Path('/data/qq_hunt/round3/exhaust_probe')
OUT.mkdir(parents=True, exist_ok=True)
QQ=re.compile(r'(QQ|qq|企鹅|扣扣|号码|号商|发卡|已售|库存|/shop|月卡|三网)',re.I)
REJECT=re.compile(r'(域名已过期|DNSPod|卡盾|Facebook|Instagram|小红书|苹果id|Apple ID|WhatsApp|飞机号|海外账号|博彩|威尼斯|棋牌|casino|1xbet|Non-compliance ICP)',re.I)

def curl(url, timeout=12):
    try:
        p=subprocess.run(['curl','-sL','-A','Mozilla/5.0','--max-time',str(timeout),'-x',PROXY,'-k','--connect-timeout','5',url],capture_output=True,timeout=timeout+3)
        return p.stdout.decode('utf-8','ignore')
    except Exception:
        return ''

def classify(body):
    if re.search(r'易发卡|ykfaka|YKFAKA',body,re.I): return 'YKFAKA易发卡'
    if re.search(r'异次元',body): return '异次元发卡'
    if re.search(r'独角',body): return '独角数卡'
    if re.search(r'title="商品库存">\d+个',body): return '卡网列表模板(通用自动发卡)'
    if re.search(r'靓号',body): return '靓号网/选号站'
    return '未识别模板'

def probe(host):
    for url in [f'https://{host}/shop/', f'https://{host}/', f'http://{host}/shop/']:
        body=curl(url)
        if len(body)<300: continue
        title_m=re.search(r'<title[^>]*>(.*?)</title>',body,re.I|re.S)
        title=re.sub(r'\s+',' ', re.sub(r'<[^>]+>','', title_m.group(1) if title_m else '')).strip()[:140]
        if REJECT.search(title) and not re.search(r'QQ|企鹅', title):
            continue
        strong=bool(re.search(r'QQ|企鹅|扣扣|qq号|QQ号|卖Q', body+title))
        sales=sum(int(x) for x in re.findall(r'(?:已售|销量)[^\d]{0,8}(\d+)',body))
        stock=sum(int(x) for x in re.findall(r'title="商品库存">(\d+)个',body))
        sys=classify(body)
        shopish='/shop' in url or sys!='未识别模板' or re.search(r'商品|库存|发卡',body)
        if strong and shopish:
            return {'host':host,'url':url,'title':title,'strong_qq':True,'qq':True,'sales':sales,'stock':stock,'sys':sys,'len':len(body)}
        if (strong or re.search(r'qq|faka',host,re.I)) and shopish and (stock>0 or sales>0 or sys.startswith(('YKFAKA','卡网'))):
            return {'host':host,'url':url,'title':title,'strong_qq':strong,'qq':True,'sales':sales,'stock':stock,'sys':sys,'len':len(body)}
    return {'host':host,'url':'','title':'','strong_qq':False,'qq':False,'sales':0,'stock':0,'sys':'dead','len':0}

hosts=[h.strip() for h in HOSTS_FILE.read_text().splitlines() if h.strip()]
print('probing',len(hosts),'via',PROXY,flush=True)
rows=[]
with ThreadPoolExecutor(max_workers=16) as ex:
    futs={ex.submit(probe,h):h for h in hosts}
    for i,fut in enumerate(as_completed(futs),1):
        r=fut.result(); rows.append(r)
        mark='QQ' if r.get('strong_qq') or (r.get('qq') and r.get('stock',0)>0) else ('hit' if r.get('len',0)>500 else 'dead')
        print(f"{i}/{len(hosts)} {mark} {r['host']} sales={r.get('sales')} stock={r.get('stock')} {r.get('sys')} {r.get('title','')[:50]}", flush=True)
        if i%40==0:
            (OUT/'probe_partial.json').write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')

rows.sort(key=lambda x:(-(x.get('strong_qq') or 0), -x.get('sales',0), -x.get('stock',0)))
(OUT/'probe_results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
alive=[]
for r in rows:
    if r.get('sys')=='dead': continue
    if not (r.get('strong_qq') or (r.get('qq') and (r.get('stock',0)>0 or str(r.get('sys','')).startswith(('YKFAKA','卡网'))))):
        continue
    if REJECT.search(r.get('title') or '') and not re.search(r'QQ|企鹅', r.get('title') or ''):
        continue
    alive.append(r)
(OUT/'qq_alive.json').write_text(json.dumps(alive,ensure_ascii=False,indent=2),encoding='utf-8')
print('ALIVE_QQ',len(alive),'/',len(rows),flush=True)
for r in alive:
    print('+',r['host'],r['sales'],r['stock'],r['sys'],r['url'],r['title'][:55])
