#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram QR login for cloud dig.
1) export TG_API_ID=... TG_API_HASH=...
2) python3 tmp_tg_qr_login.py
3) Scan the QR (printed URL + PNG) with Telegram mobile app
4) Session saved → run tmp_tg_member_scrape.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

OUT = Path(os.environ.get("OUT", "/workspace/tmp_member_dig/tg_api"))
OUT.mkdir(parents=True, exist_ok=True)
SESSION = os.environ.get("TG_SESSION", str(OUT / "tg_member"))


async def main():
    api_id = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")
    if not api_id or not api_hash:
        print(
            "Need TG_API_ID + TG_API_HASH first.\n"
            "Get free at https://my.telegram.org → API development tools\n"
            "(App title/short name can be anything; this is NOT your login password.)\n"
            "Then:\n"
            "  export TG_API_ID=123456\n"
            "  export TG_API_HASH=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n"
            "  python3 tmp_tg_qr_login.py",
            flush=True,
        )
        sys.exit(1)

    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError

    try:
        import qrcode
    except ImportError:
        qrcode = None

    client = TelegramClient(SESSION, int(api_id), api_hash)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(
            f"ALREADY_LOGGED_IN id={me.id} username=@{me.username} name={me.first_name}",
            flush=True,
        )
        await client.disconnect()
        return

    print("Generating QR login…", flush=True)
    qr = await client.qr_login()
    url = qr.url
    (OUT / "qr_login_url.txt").write_text(url + "\n", encoding="utf-8")
    print("QR_URL=", url, flush=True)

    if qrcode:
        img = qrcode.make(url)
        png = OUT / "qr_login.png"
        img.save(png)
        print("QR_PNG=", png, flush=True)
        # also ASCII for terminal
        qr2 = qrcode.QRCode(border=1)
        qr2.add_data(url)
        qr2.make(fit=True)
        qr2.print_ascii(invert=True)
    else:
        print("Install qrcode for PNG/ASCII: pip3 install qrcode pillow", flush=True)

    print(
        "\nScan this QR with Telegram app:\n"
        "  Settings → Devices → Link Desktop Device\n"
        "Waiting up to 120s…\n",
        flush=True,
    )

    try:
        await qr.wait(timeout=120)
    except SessionPasswordNeededError:
        pwd = os.environ.get("TG_2FA_PASSWORD")
        if not pwd:
            print(
                "NEED_2FA: account has cloud password. "
                "export TG_2FA_PASSWORD='your_2fa' and re-run.",
                flush=True,
            )
            await client.disconnect()
            sys.exit(3)
        await client.sign_in(password=pwd)
    except asyncio.TimeoutError:
        # refresh once
        print("QR expired, regenerating once…", flush=True)
        qr = await client.qr_login()
        (OUT / "qr_login_url.txt").write_text(qr.url + "\n", encoding="utf-8")
        print("QR_URL=", qr.url, flush=True)
        if qrcode:
            img = qrcode.make(qr.url)
            img.save(OUT / "qr_login.png")
            qr2 = qrcode.QRCode(border=1)
            qr2.add_data(qr.url)
            qr2.make(fit=True)
            qr2.print_ascii(invert=True)
        try:
            await qr.wait(timeout=120)
        except SessionPasswordNeededError:
            pwd = os.environ.get("TG_2FA_PASSWORD")
            if not pwd:
                print("NEED_2FA: export TG_2FA_PASSWORD and re-run.", flush=True)
                await client.disconnect()
                sys.exit(3)
            await client.sign_in(password=pwd)
        except asyncio.TimeoutError:
            print("TIMEOUT: no scan within time window.", flush=True)
            await client.disconnect()
            sys.exit(4)

    me = await client.get_me()
    print(
        f"LOGIN_OK id={me.id} username=@{me.username} name={me.first_name}",
        flush=True,
    )
    print(f"SESSION={SESSION}.session", flush=True)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
