#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Join Telegram groups / scrape member bios for shop websites.

Requires a real Telegram user login (NOT a bot):
  export TG_API_ID=123456
  export TG_API_HASH=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  export TG_SESSION=/data/qq_hunt/tg_member.session   # optional path
  # first run will ask phone + code in the terminal

Usage:
  python3 tmp_tg_member_scrape.py ooooy xaioqiaochuhai8 yoooo
  python3 tmp_tg_member_scrape.py --invite '+hqg1wLpkHEo4ZjFl' '+u50BFdb73wszNDQ9'
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

try:
    from telethon import TelegramClient
    from telethon.tl.functions.channels import GetParticipantsRequest
    from telethon.tl.functions.messages import GetFullChatRequest, CheckChatInviteRequest, ImportChatInviteRequest
    from telethon.tl.types import (
        ChannelParticipantsSearch,
        Channel,
        Chat,
        User,
        ChatInviteAlready,
        ChatInvite,
    )
except ImportError:
    print("Install: pip3 install telethon", file=sys.stderr)
    sys.exit(2)

OUT = Path(os.environ.get("OUT", "/workspace/tmp_member_dig/tg_api"))
OUT.mkdir(parents=True, exist_ok=True)

HOST_RE = re.compile(
    r"(?:https?://)?((?:[a-z0-9-]+\.)+(?:top|lol|cc|vip|com|cn|one|icu|xyz|shop|net|pw|hk|me|site|store|online|club|fun|info|io|tv|pro))",
    re.I,
)
BAD = re.compile(r"(t\.me|telegram|github|google|baidu|w3\.org|cloudflare)", re.I)
QQ = re.compile(r"(QQ|qq|企鹅|扣扣|发卡|号商|/shop)", re.I)


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


async def mine_user(client, u, hosts_counter, members, seen_ids, force_full=False):
    if not isinstance(u, User) or u.id in seen_ids:
        return
    seen_ids.add(u.id)
    uname = u.username or ""
    name = " ".join(x for x in [u.first_name or "", u.last_name or ""] if x)
    prelim = " ".join([name, uname])
    # Full bio only when looks shop-related (or forced from message senders)
    about = ""
    want_full = force_full or bool(QQ.search(prelim)) or bool(extract_hosts(prelim))
    if want_full:
        try:
            from telethon.tl.functions.users import GetFullUserRequest

            fu = await client(GetFullUserRequest(u))
            about = getattr(fu.full_user, "about", "") or ""
        except Exception:
            about = ""
    blob = " ".join([name, uname, about])
    hosts = extract_hosts(blob)
    for h in hosts:
        hosts_counter[h] += 1
    if hosts or QQ.search(blob):
        members.append(
            {
                "id": u.id,
                "username": uname,
                "name": name,
                "about": about[:400],
                "hosts": hosts,
                "qqish": bool(QQ.search(blob)),
                "bot": bool(getattr(u, "bot", False)),
            }
        )


async def mine_entity(client, ent, limit_members=5000, limit_messages=800):
    title = getattr(ent, "title", None) or getattr(ent, "username", None) or str(ent.id)
    username = getattr(ent, "username", None)
    row = {
        "id": ent.id,
        "title": title,
        "username": username,
        "members": [],
        "hosts": Counter(),
        "msg_hosts": Counter(),
    }
    seen = set()
    n = 0

    # 1) participants (megagroups)
    try:
        async for u in client.iter_participants(ent, limit=limit_members):
            if not isinstance(u, User):
                continue
            await mine_user(client, u, row["hosts"], row["members"], seen, force_full=False)
            n += 1
            if n % 100 == 0:
                await asyncio.sleep(0.1)
            if n % 500 == 0:
                print(f"  …{username or title}: members {n} hits {len(row['members'])}", flush=True)
    except Exception as e:
        row["error"] = str(e)[:240]
        print(f"  participants_err {username or title}: {row['error']}", flush=True)

    # 2) recent messages: extract URLs + mine senders (covers channels / hidden members)
    msg_n = 0
    try:
        async for msg in client.iter_messages(ent, limit=limit_messages):
            msg_n += 1
            text = msg.message or ""
            for h in extract_hosts(text):
                row["msg_hosts"][h] += 1
                row["hosts"][h] += 1
            # entities / buttons sometimes hold urls
            for ent_obj in getattr(msg, "entities", None) or []:
                url = getattr(ent_obj, "url", None)
                if url:
                    for h in extract_hosts(url):
                        row["msg_hosts"][h] += 1
                        row["hosts"][h] += 1
            sender = None
            try:
                sender = await msg.get_sender()
            except Exception:
                sender = None
            if isinstance(sender, User):
                await mine_user(
                    client, sender, row["hosts"], row["members"], seen, force_full=True
                )
            if msg_n % 100 == 0:
                await asyncio.sleep(0.15)
                print(f"  …{username or title}: msgs {msg_n}", flush=True)
    except Exception as e:
        row["msg_error"] = str(e)[:240]
        print(f"  messages_err {username or title}: {row['msg_error']}", flush=True)

    return {
        "id": row["id"],
        "title": row["title"],
        "username": row["username"],
        "scanned": n,
        "messages": msg_n,
        "member_hits": row["members"],
        "hosts": row["hosts"].most_common(),
        "msg_hosts": row["msg_hosts"].most_common(),
        "error": row.get("error"),
        "msg_error": row.get("msg_error"),
    }


async def join_invite(client, code: str):
    code = code.lstrip("+")
    try:
        inv = await client(CheckChatInviteRequest(code))
    except Exception as e:
        return None, f"check_fail:{e}"
    if isinstance(inv, ChatInviteAlready):
        return inv.chat, "already"
    try:
        updates = await client(ImportChatInviteRequest(code))
        chats = getattr(updates, "chats", []) or []
        return (chats[0] if chats else None), "joined"
    except Exception as e:
        return None, f"join_fail:{e}"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*", help="public usernames")
    ap.add_argument("--invite", nargs="*", default=[], help="invite hash without t.me/")
    ap.add_argument("--invite-file", default="", help="file with one invite hash per line")
    ap.add_argument("--limit", type=int, default=5000)
    args = ap.parse_args()
    if args.invite_file:
        p = Path(args.invite_file)
        if p.exists():
            args.invite = list(args.invite) + [
                ln.strip().lstrip("+")
                for ln in p.read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.startswith("#")
            ]

    api_id = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")
    if not api_id or not api_hash:
        print(
            "Missing TG_API_ID / TG_API_HASH.\n"
            "Get them at https://my.telegram.org → API development tools\n"
            "Then: export TG_API_ID=... TG_API_HASH=...",
            file=sys.stderr,
        )
        sys.exit(1)

    session = os.environ.get("TG_SESSION", str(OUT / "tg_member"))
    client = TelegramClient(session, int(api_id), api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print("Not logged in. Run tmp_tg_qr_login.py first.", file=sys.stderr)
        await client.disconnect()
        sys.exit(1)
    me = await client.get_me()
    print(f"logged_in id={me.id} @{me.username} {me.first_name}", flush=True)

    results = []
    all_hosts = Counter()
    person = []

    for name in args.targets:
        name = name.lstrip("@")
        try:
            ent = await client.get_entity(name)
        except Exception as e:
            print("fail_entity", name, e)
            continue
        # join public channel/megagroup if needed
        try:
            from telethon.tl.functions.channels import JoinChannelRequest

            if isinstance(ent, Channel):
                await client(JoinChannelRequest(ent))
                print("joined_public", name, flush=True)
        except Exception as e:
            print("join_public_note", name, str(e)[:120], flush=True)
        print("scraping", name, flush=True)
        r = await mine_entity(client, ent, limit_members=args.limit)
        results.append(r)
        for h, n in r.get("hosts") or []:
            all_hosts[h] += n
        for m in r.get("member_hits") or []:
            person.append({"group": name, **m})
        print(
            "done",
            name,
            "members",
            r.get("scanned"),
            "msgs",
            r.get("messages"),
            "hits",
            len(r.get("member_hits") or []),
            "hosts",
            len(r.get("hosts") or []),
            "err",
            r.get("error"),
            flush=True,
        )
        # checkpoint after each group
        (OUT / "group_member_sites.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (OUT / "member_person_sites.json").write_text(
            json.dumps(person, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (OUT / "member_hosts.txt").write_text(
            "\n".join(f"{h}\t{n}" for h, n in all_hosts.most_common()), encoding="utf-8"
        )

    for inv in args.invite:
        code = inv.replace("https://t.me/", "").replace("t.me/", "").lstrip("+")
        ent, status = await join_invite(client, code)
        print("invite", code, status, getattr(ent, "title", None), flush=True)
        if not ent:
            continue
        r = await mine_entity(client, ent, limit_members=args.limit)
        r["invite"] = code
        r["join_status"] = status
        results.append(r)
        for h, n in r.get("hosts") or []:
            all_hosts[h] += n
        for m in r.get("member_hits") or []:
            person.append({"group": r.get("title"), **m})

    (OUT / "group_member_sites.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "member_person_sites.json").write_text(
        json.dumps(person, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "member_hosts.txt").write_text(
        "\n".join(f"{h}\t{n}" for h, n in all_hosts.most_common()), encoding="utf-8"
    )
    print("HOSTS", all_hosts.most_common(50))
    print("PERSON", len(person))
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
