
import re,subprocess,json
HOST='qqq.lc';BASE=f'https://{HOST}'
UA='Mozilla/5.0'
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
def curl(path, method='GET', data=None, headers=None):
    cmd=['curl','-sk','-D','-','--max-time','35','-A',UA,'--max-redirs','0']
    if jar.c: cmd+=['-H',f'Cookie: {jar.header()}']
    if headers:
        for k,v in headers.items(): cmd+=['-H',f'{k}: {v}']
    url=BASE+path
    if method=='POST':
        cmd+=['-X','POST','-H','Content-Type: application/x-www-form-urlencoded','--data-binary',data or '']
    cmd.append(url)
    p=subprocess.run(cmd,capture_output=True,timeout=50)
    text=(p.stdout or b'').decode('utf-8','replace')
    hdr,body=(text.split('\r\n\r\n',1)+[''])[:2] if '\r\n\r\n' in text else (text,'')
    jar.absorb(hdr); return body
body=curl('/')
m=re.search(r"setCookie\('ccsafe_defend',(.+?)\);",body)
val=subprocess.check_output(['node','-e','console.log('+m.group(1)+')']).decode().strip()
jar.c['ccsafe_defend']=val; jar.c['ccsafe_defend_time']='2'
curl('/'); curl('/user/login.php')
xhr={'X-Requested-With':'XMLHttpRequest'}
out={}
for qq in ['132','152','172','182','183','18','15']:
    j=json.loads(curl('/ajax.php?act=query',method='POST',data=f'querytype=1&qq={qq}&page=1',headers=xhr))
    rows=[]
    for o in list((j.get('data') or {}).values())[:5]:
        rows.append({k:o.get(k) for k in ('id','input','name','money','status','skey','addtime')})
    out[qq]={'total':j.get('total'),'rows':rows}
print(json.dumps(out,ensure_ascii=False,indent=2))
