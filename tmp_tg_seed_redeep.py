#!/usr/bin/env python3
import asyncio, json, os, re
from collections import Counter
from pathlib import Path
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import Channel, User

OUT=Path('/workspace/tmp_member_dig/tg_api')
HOST_RE=re.compile(r"(?:https?://)?((?:[a-z0-9-]+\.)+(?:top|lol|cc|vip|com|cn|one|icu|xyz|shop|net|pw|hk|me|site|store|online|club|fun|info|io|tv|pro))", re.I)
BAD=re.compile(r"(t\.me|telegram|github|google|baidu|tronscan|docs\.qq|ysepan|gmail|weibo|alipay|cloudflare)", re.I)
QQ=re.compile(r"(QQ|qq|企鹅|扣扣|发卡|号商|/shop|美卡|国卡|太阳|月亮|皇冠|扫码)", re.I)

def clean(h):
    h=h.lower().removeprefix('www.').strip('.')
    if not re.match(r'^[a-z0-9][a-z0-9.-]+\.[a-z]{2,24}$', h): return None
    if BAD.search(h) or not (5<=len(h)<=58): return None
    return h

def hosts(text):
    out=[]
    for h in HOST_RE.findall(text or ''):
        c=clean(h)
        if c and c not in out: out.append(c)
    return out

async def main():
    c=TelegramClient(str(OUT/'tg_member'), int(os.environ['TG_API_ID']), os.environ['TG_API_HASH'])
    await c.connect()
    assert await c.is_user_authorized()
    allh=Counter(); people=[]; groups=[]
    seeds=['ooooy','yoooo','kehu','kfcgx','jiu224','chgx','hhgx','hxgx']
    for name in seeds:
        try:
            ent=await c.get_entity(name)
        except Exception as e:
            print('fail', name, e); continue
        try:
            if isinstance(ent, Channel):
                await c(JoinChannelRequest(ent))
        except Exception:
            pass
        title=getattr(ent,'title',None) or name
        print('seed', name, title, flush=True)
        row={'name':name,'title':title,'hosts':Counter(),'msgs':0,'hits':0}
        seen=set()
        async for msg in c.iter_messages(ent, limit=2000):
            row['msgs']+=1
            text=msg.message or ''
            for h in hosts(text):
                row['hosts'][h]+=1; allh[h]+=1
            for ent_obj in getattr(msg,'entities',None) or []:
                url=getattr(ent_obj,'url',None)
                if url:
                    for h in hosts(url):
                        row['hosts'][h]+=1; allh[h]+=1
            try:
                sender=await msg.get_sender()
            except Exception:
                sender=None
            if isinstance(sender, User) and sender.id not in seen:
                seen.add(sender.id)
                about=''
                try:
                    fu=await c(GetFullUserRequest(sender))
                    about=getattr(fu.full_user,'about','') or ''
                except Exception:
                    pass
                uname=sender.username or ''
                name2=' '.join(x for x in [sender.first_name or '', sender.last_name or ''] if x)
                blob=f'{name2} {uname} {about}'
                hs=hosts(blob)
                for h in hs: allh[h]+=1
                if hs or QQ.search(blob):
                    people.append({'group':title,'username':uname,'name':name2,'about':about[:400],'hosts':hs})
                    row['hits']+=1
            if row['msgs']%300==0:
                print(f'  {name} msgs={row["msgs"]} hosts={len(row["hosts"])} hits={row["hits"]}', flush=True)
        row['hosts']=row['hosts'].most_common()
        groups.append(row)
        print('done', name, row['msgs'], len(row['hosts']), row['hits'], flush=True)
        (OUT/'seed_redeep_hosts.txt').write_text('\n'.join(f'{h}\t{n}' for h,n in allh.most_common()), encoding='utf-8')
        (OUT/'seed_redeep_people.json').write_text(json.dumps(people, ensure_ascii=False, indent=2), encoding='utf-8')
        (OUT/'seed_redeep_groups.json').write_text(json.dumps(groups, ensure_ascii=False, indent=2), encoding='utf-8')
    print('TOTAL_HOSTS', allh.most_common(60), flush=True)
    print('PEOPLE', len(people), flush=True)
    await c.disconnect()

asyncio.run(main())
