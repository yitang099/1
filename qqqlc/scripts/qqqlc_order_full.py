#!/usr/bin/env python3
import re, subprocess, json, time
from pathlib import Path

HOST='qqq.lc'; BASE=f'https://{HOST}'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
OUT=Path('/tmp/qqqlc_out5'); OUT.mkdir(exist_ok=True)

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

def curl(path, method='GET', data=None, headers=None, t=45):
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
    body=curl('/')  # may 302 empty
    # follow login for mysid
    curl('/user/login.php')

pass_cc()
xhr={'X-Requested-With':'XMLHttpRequest'}

def query(qq, page=1):
    body=curl('/ajax.php?act=query',method='POST',data=f'querytype=1&qq={qq}&page={page}',headers=xhr)
    return json.loads(body)

def order_detail(oid, skey):
    body=curl('/ajax.php?act=order',method='POST',data=f'id={oid}&skey={skey}',headers=xhr)
    return body

# harvest status 4 and 2 and some 1 from qq=1 pages looking for list/kami
harvest=[]
for qq in list('123456789')+['11','12','qq']:
    j=query(qq,1)
    total=j.get('total') or 0
    pages=min(20, max(1,(total+9)//10))
    for p in range(1, pages+1):
        if p>1:
            j=query(qq,p)
            time.sleep(0.3)
        data=j.get('data') or {}
        if not isinstance(data,dict): continue
        for o in data.values():
            if o.get('status') in (2,3,4,5) or o.get('endtime') or o.get('result'):
                harvest.append(o)
    time.sleep(0.35)

# dedupe
uh={o['id']:o for o in harvest}
print('HARVEST', len(uh), 'by_st', {st:sum(1 for o in uh.values() if o.get('status')==st) for st in set(o.get('status') for o in uh.values())})

details=[]
kami_like=[]
for o in uh.values():
    body=order_detail(o['id'], o['skey'])
    (OUT/f'ord_{o["id"]}.json').write_text(body)
    try:
        j=json.loads(body)
    except Exception:
        print('BAD', o['id'], body[:100]); continue
    details.append(j)
    print('====', o['id'], 'st', o.get('status'), 'keys', sorted(j.keys()))
    print(json.dumps(j, ensure_ascii=False)[:1500])
    blob=json.dumps(j, ensure_ascii=False)
    if j.get('list') or j.get('result') or j.get('km') or '卡密' in blob or '验证码' in blob or 'code' in str(j.get('list')):
        kami_like.append(j)
        print('*** INTERESTING ***')
    time.sleep(0.35)

print('KAMI_LIKE_COUNT', len(kami_like))

# also dump a few status=1 full details to see list field when SMS arrives
j=query('1',1)
for o in list((j.get('data') or {}).values())[:5]:
    body=order_detail(o['id'], o['skey'])
    jj=json.loads(body)
    print('ST1', o['id'], 'list=', jj.get('list'), 'status_in_detail?', jj.get('status'), 'full_keys', sorted(jj.keys()))
    print(json.dumps(jj, ensure_ascii=False)[:1200])
    time.sleep(0.3)

# save summary
(OUT/'harvest_ids.json').write_text(json.dumps(list(uh.keys())))
(OUT/'details_meta.json').write_text(json.dumps([
    {'payorder':d.get('payorder'), 'list':d.get('list'), 'status_fields': {k:d.get(k) for k in d if k in ('list','result','km','code','msg','endtime','usetime','dj_money','status')}}
    for d in details
], ensure_ascii=False, indent=2))
print('DONE')
