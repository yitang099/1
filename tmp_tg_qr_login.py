#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram QR login with auto-refresh (token expires ~30s).
Must scan via: Telegram → Settings → Devices → Link Desktop Device
(NOT WeChat / system camera)
"""
from __future__ import annotations

import asyncio
import base64
import io
import os
import sys
import time
from pathlib import Path

OUT = Path(os.environ.get("OUT", "/workspace/tmp_member_dig/tg_api"))
OUT.mkdir(parents=True, exist_ok=True)
SESSION = os.environ.get("TG_SESSION", str(OUT / "tg_member"))
TOTAL_WAIT = int(os.environ.get("TG_QR_WAIT", "600"))
REFRESH_EVERY = float(os.environ.get("TG_QR_REFRESH", "25"))


def save_qr_assets(url: str, qrcode_mod) -> None:
    (OUT / "qr_login_url.txt").write_text(url + "\n", encoding="utf-8")
    img = qrcode_mod.make(url)
    png_path = OUT / "qr_login.png"
    img.save(png_path)

    # big nearest-neighbor for easy phone scan
    try:
        from PIL import Image

        im = Image.open(png_path)
        big = im.resize((im.width * 5, im.height * 5), Image.NEAREST)
        big_path = OUT / "qr_login_big.png"
        big.save(big_path)
        buf = io.BytesIO()
        big.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
    except Exception:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()

    ts = time.strftime("%H:%M:%S")
    html = f"""<!doctype html><html><head>
<meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="8">
<title>TG QR Login</title>
<style>
body{{margin:0;background:#0b0b0b;color:#fff;font-family:sans-serif;
display:flex;flex-direction:column;align-items:center;padding:24px}}
img{{width:min(94vw,400px);background:#fff;padding:16px;border-radius:12px}}
p{{text-align:center;max-width:440px;line-height:1.55}}
.ok{{color:#7dffa0}}.warn{{color:#ffd27d}}
.small{{opacity:.7;font-size:12px;word-break:break-all}}
</style></head><body>
<h1>马上扫这个码</h1>
<img src="data:image/png;base64,{b64}" alt="qr"/>
<p class=warn>必须用 Telegram App：设置 → 设备 → 连接桌面设备<br>
不要用微信/系统相机扫（会提示「无效二维码」）</p>
<p class=ok>本页每 8 秒自动刷新；码约 30 秒换新（更新于 {ts} UTC）</p>
<p class=small>{url}</p>
</body></html>"""
    (OUT / "tg_qr_login.html").write_text(html, encoding="utf-8")
    # artifact copy
    art = Path("/opt/cursor/artifacts")
    try:
        art.mkdir(parents=True, exist_ok=True)
        (art / "tg_qr_login.png").write_bytes(png_path.read_bytes())
        if (OUT / "qr_login_big.png").exists():
            (art / "tg_qr_login_big.png").write_bytes((OUT / "qr_login_big.png").read_bytes())
        (art / "tg_qr_login.html").write_text(html, encoding="utf-8")
    except Exception:
        pass


async def publish_to_jump() -> None:
    """Best-effort sync to jump HTTP root."""
    host = os.environ.get("JUMP_HOST", "124.248.67.170")
    user = os.environ.get("JUMP_USER", "root")
    pwd = os.environ.get("JUMP_PASS", "UzHlZQDUy7XP")
    remote = os.environ.get("JUMP_DIR", "/data/qq_hunt/round3")
    try:
        import paramiko
    except ImportError:
        # fallback scp via subprocess if available
        import shutil
        import subprocess

        if not shutil.which("sshpass"):
            return
        env = os.environ.copy()
        env["SSHPASS"] = pwd
        for local, remote_name in [
            (OUT / "tg_qr_login.html", "tg_qr_login.html"),
            (OUT / "qr_login_big.png", "tg_qr_login.png"),
        ]:
            if not local.exists():
                continue
            subprocess.run(
                [
                    "sshpass",
                    "-e",
                    "scp",
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    str(local),
                    f"{user}@{host}:{remote}/{remote_name}",
                ],
                env=env,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return

    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(host, username=user, password=pwd, timeout=20, allow_agent=False, look_for_keys=False)
        sftp = c.open_sftp()
        sftp.put(str(OUT / "tg_qr_login.html"), f"{remote}/tg_qr_login.html")
        big = OUT / "qr_login_big.png"
        if big.exists():
            sftp.put(str(big), f"{remote}/tg_qr_login.png")
        else:
            sftp.put(str(OUT / "qr_login.png"), f"{remote}/tg_qr_login.png")
        sftp.close()
        c.close()
    except Exception as e:
        print(f"publish_warn: {e}", flush=True)


async def main():
    api_id = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")
    if not api_id or not api_hash:
        print("Need TG_API_ID + TG_API_HASH", flush=True)
        sys.exit(1)

    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError

    try:
        import qrcode
    except ImportError:
        print("pip3 install qrcode pillow", flush=True)
        sys.exit(1)

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

    print("Generating auto-refreshing QR login…", flush=True)
    print(
        "Scan ONLY inside Telegram:\n"
        "  Settings → Devices → Link Desktop Device\n"
        "Open: http://124.248.67.170:18888/tg_qr_login.html\n"
        f"Waiting up to {TOTAL_WAIT}s with refresh every {REFRESH_EVERY}s…\n",
        flush=True,
    )

    qr = await client.qr_login()
    save_qr_assets(qr.url, qrcode)
    print("QR_URL=", qr.url, flush=True)
    await publish_to_jump()

    deadline = time.time() + TOTAL_WAIT
    while time.time() < deadline:
        remaining = max(1.0, min(REFRESH_EVERY, deadline - time.time()))
        try:
            await qr.wait(timeout=remaining)
            break
        except SessionPasswordNeededError:
            pwd = os.environ.get("TG_2FA_PASSWORD")
            if not pwd:
                print(
                    "NEED_2FA: account has cloud password. "
                    "export TG_2FA_PASSWORD='...' and re-run / tell me the password.",
                    flush=True,
                )
                await client.disconnect()
                sys.exit(3)
            await client.sign_in(password=pwd)
            break
        except asyncio.TimeoutError:
            # token expired or refresh window — recreate
            try:
                await qr.recreate()
            except Exception:
                qr = await client.qr_login()
            save_qr_assets(qr.url, qrcode)
            print(f"QR_REFRESH {time.strftime('%H:%M:%S')} URL={qr.url}", flush=True)
            await publish_to_jump()
    else:
        print("TIMEOUT: no scan within time window.", flush=True)
        await client.disconnect()
        sys.exit(4)

    if not await client.is_user_authorized():
        # wait() returned without auth in rare cases
        print("LOGIN_FAIL: not authorized after wait", flush=True)
        await client.disconnect()
        sys.exit(5)

    me = await client.get_me()
    print(
        f"LOGIN_OK id={me.id} username=@{me.username} name={me.first_name}",
        flush=True,
    )
    print(f"SESSION={SESSION}.session", flush=True)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
