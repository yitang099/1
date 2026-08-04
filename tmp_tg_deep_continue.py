#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Continue Telegram dig: retry invites, follow bios usernames/channels, mine hosts."""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import FloodWaitError, UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import Channel, Chat, ChatInviteAlready, User

OUT = Path(os.environ.get("OUT", "/workspace/tmp_member_dig/tg_api"))
OUT.mkdir(parents=True, exist_ok=True)
SESSION = os.environ.get("TG_SESSION", str(OUT / "tg_member"))

HOST_RE = re.compile(
    r"(?:https?://)?((?:[a-z0-9-]+\.)+(?:top|lol|cc|vip|com|cn|one|icu|xyz|shop|net|pw|hk|me|site|store|online|club|fun|info|io|tv|pro))",
    re.I,
)
BAD = re.compile(
    r"(t\.me|telegram|github|google|baidu|w3\.org|cloudflare|tronscan|docs\.qq|ysepan|gmail\.com|weibo\.com|alipay)",
    re.I,
)
QQ = re.compile(r"(QQ|qq|企鹅|扣扣|发卡|号商|/shop|美卡|国卡|太阳|月亮|皇冠|扫码)", re.I)
USER_RE = re.compile(r"(?:@|t\.me/)([A-Za-z][A-Za-z0-9_]{3,31})")
INV_RE = re.compile(r"t\.me/\+([A-Za-z0-9_-]+)")


def clean_host(h: str):
    h = h.lower().removeprefix("www.").strip(".")
    if not re.match(r"^[a-z0-9][a-z0-9.-]+\.[a-z]{2,24}$", h):
        return None
    if BAD.search(h) or not (5 <= len(h) <= 58):
        return None
    return h


def extract_hosts(text: str):
    out = []
    for h in HOST_RE.findall(text or ""):
        ch = clean_host(h)
        if ch and ch not in out:
            out.append(ch)
    return out


class Dig:
    def __init__(self, client: TelegramClient):
        self.client = client
        self.hosts = Counter()
        self.people = []
        self.groups = []
        self.seen_users = set()
        self.seen_chats = set()
        self.seen_invites = set()
        self.errors = []

    def add_hosts(self, hosts, n=1):
        for h in hosts:
            self.hosts[h] += n

    async def mine_about(self, u: User, group: str, force=False):
        if not isinstance(u, User) or u.id in self.seen_users:
            return
        self.seen_users.add(u.id)
        uname = u.username or ""
        name = " ".join(x for x in [u.first_name or "", u.last_name or ""] if x)
        prelim = f"{name} {uname}"
        about = ""
        if force or QQ.search(prelim) or extract_hosts(prelim):
            try:
                fu = await self.client(GetFullUserRequest(u))
                about = getattr(fu.full_user, "about", "") or ""
            except Exception:
                about = ""
        blob = f"{name} {uname} {about}"
        hosts = extract_hosts(blob)
        self.add_hosts(hosts)
        if hosts or QQ.search(blob):
            self.people.append(
                {
                    "id": u.id,
                    "username": uname,
                    "name": name,
                    "about": about[:400],
                    "hosts": hosts,
                    "group": group,
                }
            )
        return about

    async def mine_chat(self, ent, label: str, msg_limit=1000, member_limit=800):
        cid = getattr(ent, "id", None)
        if cid in self.seen_chats:
            return
        self.seen_chats.add(cid)
        title = getattr(ent, "title", None) or getattr(ent, "username", None) or str(cid)
        username = getattr(ent, "username", None)
        print(f"mine_chat {label} | {title} @{username}", flush=True)
        row = {
            "id": cid,
            "title": title,
            "username": username,
            "label": label,
            "hosts": Counter(),
            "msg_hosts": Counter(),
            "members_scanned": 0,
            "messages": 0,
            "hits": 0,
        }

        # participants (megagroup)
        try:
            n = 0
            async for u in self.client.iter_participants(ent, limit=member_limit):
                if not isinstance(u, User):
                    continue
                before = len(self.people)
                await self.mine_about(u, title, force=False)
                if len(self.people) > before:
                    row["hits"] += 1
                n += 1
                if n % 400 == 0:
                    print(f"  members {n} hits {row['hits']}", flush=True)
                    await asyncio.sleep(0.2)
            row["members_scanned"] = n
        except Exception as e:
            row["member_error"] = str(e)[:200]
            print(f"  member_err {e}", flush=True)

        # messages
        try:
            m = 0
            async for msg in self.client.iter_messages(ent, limit=msg_limit):
                m += 1
                text = msg.message or ""
                hs = extract_hosts(text)
                for h in hs:
                    row["msg_hosts"][h] += 1
                    row["hosts"][h] += 1
                    self.hosts[h] += 1
                for ent_obj in getattr(msg, "entities", None) or []:
                    url = getattr(ent_obj, "url", None)
                    if url:
                        for h in extract_hosts(url):
                            row["msg_hosts"][h] += 1
                            self.hosts[h] += 1
                try:
                    sender = await msg.get_sender()
                except Exception:
                    sender = None
                if isinstance(sender, User):
                    before = len(self.people)
                    await self.mine_about(sender, title, force=True)
                    if len(self.people) > before:
                        row["hits"] += 1
                if m % 200 == 0:
                    print(f"  msgs {m} hosts {len(row['msg_hosts'])}", flush=True)
                    await asyncio.sleep(0.1)
            row["messages"] = m
        except Exception as e:
            row["msg_error"] = str(e)[:200]
            print(f"  msg_err {e}", flush=True)

        row["hosts"] = row["hosts"].most_common()
        row["msg_hosts"] = row["msg_hosts"].most_common()
        self.groups.append(row)
        self.checkpoint()
        print(
            f"done_chat {title} members={row['members_scanned']} msgs={row['messages']} "
            f"hits={row['hits']} hosts={len(row['hosts'])}",
            flush=True,
        )

    async def join_invite(self, code: str):
        code = code.lstrip("+")
        if code in self.seen_invites:
            return None, "seen"
        self.seen_invites.add(code)

        async def check():
            return await self.client(CheckChatInviteRequest(code))

        try:
            inv = await check()
        except FloodWaitError as e:
            wait = min(int(e.seconds) + 2, 300)
            print(f"invite_flood {code} wait {wait}", flush=True)
            await asyncio.sleep(wait)
            try:
                inv = await check()
            except Exception as e2:
                return None, f"check_fail:{e2}"
        except Exception as e:
            return None, f"check_fail:{e}"

        if isinstance(inv, ChatInviteAlready):
            return inv.chat, "already"

        async def import_invite():
            return await self.client(ImportChatInviteRequest(code))

        try:
            result = await import_invite()
        except UserAlreadyParticipantError:
            try:
                inv2 = await check()
                if isinstance(inv2, ChatInviteAlready):
                    return inv2.chat, "already"
            except Exception:
                pass
            return None, "already_no_chat"
        except FloodWaitError as e:
            wait = min(int(e.seconds) + 2, 300)
            print(f"join_flood {code} wait {wait}", flush=True)
            await asyncio.sleep(wait)
            try:
                result = await import_invite()
            except UserAlreadyParticipantError:
                try:
                    inv2 = await check()
                    if isinstance(inv2, ChatInviteAlready):
                        return inv2.chat, "already"
                except Exception:
                    pass
                return None, "already_no_chat"
            except Exception as e2:
                return None, f"join_fail:{e2}"
        except Exception as e:
            # pending approval etc.
            return None, f"join_fail:{type(e).__name__}:{e}"

        chats = list(getattr(result, "chats", None) or [])
        if chats:
            return chats[0], "joined"
        # re-check: after join, invite preview becomes ChatInviteAlready
        try:
            inv3 = await check()
            if isinstance(inv3, ChatInviteAlready):
                return inv3.chat, "joined_via_check"
        except Exception:
            pass
        return None, "joined_empty"

    async def follow_username(self, name: str):
        name = name.lstrip("@")
        try:
            ent = await self.client.get_entity(name)
        except Exception as e:
            self.errors.append({"user": name, "err": str(e)[:160]})
            return
        if isinstance(ent, User):
            await self.mine_about(ent, f"@{name}", force=True)
            return
        if isinstance(ent, Channel):
            try:
                await self.client(JoinChannelRequest(ent))
            except Exception:
                pass
            # channels: more messages; megagroups: members+messages
            ml = 1200 if not getattr(ent, "megagroup", False) else 900
            mem = 0 if not getattr(ent, "megagroup", False) else 600
            await self.mine_chat(ent, f"@{name}", msg_limit=ml, member_limit=mem)

    def checkpoint(self):
        (OUT / "deep2_groups.json").write_text(
            json.dumps(self.groups, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (OUT / "deep2_people.json").write_text(
            json.dumps(self.people, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (OUT / "deep2_hosts.txt").write_text(
            "\n".join(f"{h}\t{n}" for h, n in self.hosts.most_common()), encoding="utf-8"
        )
        (OUT / "deep2_errors.json").write_text(
            json.dumps(self.errors[-200:], ensure_ascii=False, indent=2), encoding="utf-8"
        )


async def main():
    api_id = os.environ["TG_API_ID"]
    api_hash = os.environ["TG_API_HASH"]
    client = TelegramClient(SESSION, int(api_id), api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print("NOT_LOGGED_IN", flush=True)
        sys.exit(1)
    me = await client.get_me()
    print(f"logged_in {me.id} {me.first_name}", flush=True)

    dig = Dig(client)

    # seed previous hosts so counts accumulate separately but we keep deep2 clean
    # 1) retry + new invites
    invites = []
    for p in [
        OUT / "invite_codes.txt",
        OUT / "follow_invites.txt",
    ]:
        if p.exists():
            invites += [ln.strip().lstrip("+") for ln in p.read_text().splitlines() if ln.strip()]
    # failed ones first
    priority = [
        "JUpht_a3F_1mZTFl",
        "ebO-Tk3cv79jMTQ9",
        "oQRtuHMYY6A1Zjk1",
        "Xs0EB650qHdiOGI1",
        "qQG3yVWdP5NhYmM0",
        "brhoK-rrz283OWM1",
        "DVYH2Ve6Q6ZhNmJl",
        "p6y-ynlLuFFjOTlh",
        "2cgLBXccCa1mNjll",
        "pa0_PJWny1UwZTM1",
        "p4Bt4W4bUWRkYjc9",
        "-CVY42-PnxkyYjZl",
        "Z_e7aqelSCY2YzFl",
        "dMzKTsRlpW03OWM1",  # elmqq notify from bio
    ]
    ordered = []
    for c in priority + invites:
        if c and c not in ordered:
            ordered.append(c)

    # 0) mine existing dialogs that look QQ-related (already joined)
    print("scan_dialogs…", flush=True)
    try:
        async for d in client.iter_dialogs(limit=200):
            ent = d.entity
            title = (d.title or "") + " " + (getattr(ent, "username", None) or "")
            if not QQ.search(title):
                continue
            if isinstance(ent, (Channel, Chat)):
                await dig.mine_chat(ent, f"dialog:{d.title}", msg_limit=800, member_limit=300)
    except Exception as e:
        print("dialogs_err", e, flush=True)

    # 1) follow QQ-looking usernames FIRST (no invite flood)
    users = []
    up = OUT / "follow_users.txt"
    if up.exists():
        users = [ln.strip() for ln in up.read_text().splitlines() if ln.strip()]
    def score(u):
        s = 0
        lu = u.lower()
        for k in ("qq", "hao", "fk", "shop", "kami", "card", "qun", "maiqq", "bwqq", "qun"):
            if k in lu:
                s += 2
        return s

    users = sorted(set(users), key=lambda u: (-score(u), u))[:100]
    print(f"follow_users {len(users)}", flush=True)
    for i, u in enumerate(users, 1):
        print(f"follow[{i}/{len(users)}] @{u}", flush=True)
        try:
            await dig.follow_username(u)
        except FloodWaitError as e:
            print(f"follow_flood wait {e.seconds}", flush=True)
            await asyncio.sleep(min(int(e.seconds) + 1, 90))
        except Exception as e:
            dig.errors.append({"user": u, "err": str(e)[:160]})
        if i % 8 == 0:
            dig.checkpoint()
            await asyncio.sleep(1.2)

    # 2) invites slowly (check-already first)
    print(f"invites_to_try {len(ordered)}", flush=True)
    for i, code in enumerate(ordered, 1):
        ent, status = await dig.join_invite(code)
        print(f"invite[{i}/{len(ordered)}] {code} {status} {getattr(ent,'title',None)}", flush=True)
        if ent:
            await dig.mine_chat(ent, f"invite:{code}", msg_limit=900, member_limit=400)
        # be gentle on join rate
        await asyncio.sleep(8 if "fail" in status or "flood" in status else 5)

    # 3) re-deep high value public seeds with more messages
    for name in ["ooooy", "yoooo", "kehu", "kfcgx", "jiu224", "chgx", "hhgx", "hxgx"]:
        try:
            ent = await client.get_entity(name)
            try:
                if isinstance(ent, Channel):
                    await client(JoinChannelRequest(ent))
            except Exception:
                pass
            await dig.mine_chat(ent, f"seed:{name}", msg_limit=1500, member_limit=150)
        except Exception as e:
            print("seed_fail", name, e, flush=True)

    dig.checkpoint()
    print("HOSTS", dig.hosts.most_common(80), flush=True)
    print("PEOPLE", len(dig.people), "GROUPS", len(dig.groups), flush=True)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
