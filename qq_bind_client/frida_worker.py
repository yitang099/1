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


def _qq_targets(device) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for proc in device.enumerate_processes():
        name = proc.name or ""
        if QQ_PKG not in name:
            continue
        found.append((int(proc.pid), name))

    def rank(item: tuple[int, str]) -> tuple[int, str]:
        n = item[1]
        if n == QQ_PKG:
            return (0, n)
        if ":MSF" in n.upper():
            return (1, n)
        return (2, n)

    found.sort(key=rank)
    if not found:
        raise RuntimeError("未找到 QQ 进程，请打开 QQ 并停在验证码页")
    return found


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
        _emit({"type": "ready", "stage": payload.get("stage", "")})
    elif kind == "no_java":
        _emit({"type": "no_java", "pid": payload.get("pid")})
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


def _inject_one(device, parser_mod, hook_source: str, pid: int, name: str) -> bool:
    prefix = "var __HOOK_MODE__ = 'targeted';\nvar __JAVA_WAIT_SEC__ = 90;\n"
    try:
        session = device.attach(pid)
    except Exception as exc:
        _emit({"type": "log", "text": f"attach 失败 {name} pid={pid}: {exc}"})
        return False

    script = session.create_script(prefix + hook_source)
    script.on("message", lambda m, d, p=parser_mod: _on_frida_message(m, d, p))
    try:
        script.load()
    except Exception as exc:
        _emit({"type": "log", "text": f"load 失败 {name} pid={pid}: {exc}"})
        try:
            session.detach()
        except Exception:
            pass
        return False

    _emit({"type": "injected", "pid": pid, "name": name})
    return True


def cmd_inject() -> int:
    import frida
    from qq_bind_client import parse_qq_bind_uin as parser_mod

    parser_mod.run_self_test()
    _emit({"type": "log", "text": f"frida-worker {frida.__version__}"})
    device = frida.get_usb_device(timeout=12)
    hook_source = _hook_source()
    targets = _qq_targets(device)
    names = ", ".join(f"{n}:{p}" for p, n in targets)
    _emit({"type": "log", "text": f"QQ 进程: {names}"})

    injected = 0
    for pid, name in targets[:4]:
        if _inject_one(device, parser_mod, hook_source, pid, name):
            injected += 1

    if injected == 0:
        raise RuntimeError("所有进程注入失败，请确认 USB调试(安全设置) 已开")

    _emit({"type": "log", "text": f"已注入 {injected} 个进程，请立即填验证码"})
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    return 0


def cmd_diagnose() -> int:
    import frida

    _emit({"type": "log", "text": f"frida {frida.__version__}"})
    device = frida.get_usb_device(timeout=8)
    targets = _qq_targets(device)
    for pid, name in targets:
        _emit({"type": "proc", "pid": pid, "name": name})
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        _emit({"type": "error", "text": "missing command"})
        return 2
    cmd = args[0]
    try:
        if cmd == "inject":
            return cmd_inject()
        if cmd == "diagnose":
            return cmd_diagnose()
        _emit({"type": "error", "text": f"unknown command: {cmd}"})
        return 2
    except Exception as exc:
        _emit({"type": "error", "text": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
