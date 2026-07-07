#!/usr/bin/env python3
"""独立子进程运行 Frida，避免 GUI 卡死（GIL/attach 阻塞主进程）。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

QQ_PKG = "com.tencent.mobileqq"


def _emit(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def _hook_source() -> str:
    from qq_bind_client.config import APP_DIR, resource_dir

    for base in (resource_dir(), APP_DIR, Path(__file__).resolve().parent):
        p = base / "frida_hook.js"
        if p.is_file():
            return p.read_text(encoding="utf-8")
    raise FileNotFoundError("frida_hook.js not found")


def _find_main_pid(device) -> tuple[int, str]:
    main_pid = None
    main_name = QQ_PKG
    for proc in device.enumerate_processes():
        name = proc.name or ""
        if name == QQ_PKG:
            return int(proc.pid), name
        if "com.tencent.mobileqq" in name and ":MSF" not in name.upper():
            main_pid = int(proc.pid)
            main_name = name
    if main_pid:
        return main_pid, main_name
    raise RuntimeError("未找到 QQ 主进程，请打开QQ并停在验证码页")


def _on_frida_message(message, _data, parser_mod) -> None:
    if message.get("type") == "error":
        _emit({"type": "error", "text": message.get("stack") or str(message)})
        return
    if message.get("type") != "send":
        return
    payload = message.get("payload") or {}
    kind = payload.get("type")
    if kind == "log":
        _emit({"type": "log", "text": payload.get("msg", "")})
    elif kind == "ready":
        _emit({"type": "ready"})
    elif kind == "plain_qq":
        _emit({"type": "qq", "qq": payload.get("qq"), "source": payload.get("source")})
    elif kind == "tlv543":
        hex_data = (payload.get("hex") or "").replace(" ", "")
        qq = ""
        if hex_data:
            try:
                result = parser_mod.parse_auto(bytes.fromhex(hex_data))
                if result.accounts:
                    qq = result.accounts[0].key_uin
            except ValueError:
                pass
        _emit({"type": "tlv", "hex": hex_data, "qq": qq, "key": payload.get("key")})


def cmd_inject() -> int:
    import frida
    from qq_bind_client import parse_qq_bind_uin as parser_mod

    parser_mod.run_self_test()
    _emit({"type": "log", "text": f"frida-worker {frida.__version__}"})
    device = frida.get_usb_device(timeout=12)
    pid, name = _find_main_pid(device)
    _emit({"type": "log", "text": f"attach {name} pid={pid}"})
    prefix = "var __LIGHT_MODE__ = true;\nvar __JAVA_WAIT_SEC__ = 90;\n"
    session = device.attach(pid)
    script = session.create_script(prefix + _hook_source())
    script.on("message", lambda m, d: _on_frida_message(m, d, parser_mod))
    script.load()
    _emit({"type": "injected", "pid": pid, "name": name})
    _emit({"type": "log", "text": "注入完成，请填写验证码"})
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] != "inject":
        _emit({"type": "error", "text": f"unknown command: {args}"})
        return 2
    try:
        return cmd_inject()
    except Exception as exc:
        _emit({"type": "error", "text": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
