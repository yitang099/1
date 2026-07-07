#!/usr/bin/env python3
"""独立子进程运行 Frida，避免 GUI 卡死。"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

QQ_PKG = "com.tencent.mobileqq"

# 必须保持引用，否则 session 会被 GC 导致 Hook 失效
_SESSIONS: list = []


def _emit(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def _hook_source() -> str:
    from qq_bind_client.config import APP_DIR, resource_dir

    for base in (resource_dir(), APP_DIR, Path(__file__).resolve().parent):
        p = base / "frida_hook.js"
        if p.is_file():
            return p.read_text(encoding="utf-8")
    raise FileNotFoundError("frida_hook.js not found")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("command")
    p.add_argument("--adb", default="", help="adb.exe path")
    return p.parse_args(argv)


def _adb_path(ns: argparse.Namespace) -> str | None:
    from qq_bind_client.adb_helper import find_adb

    return find_adb(ns.adb or "")


def _qq_targets_from_adb(adb: str) -> list[tuple[int, str]]:
    from qq_bind_client.adb_helper import list_qq_procs_adb, wake_qq_app

    procs = list_qq_procs_adb(adb)
    main = [p for p in procs if ":MSF" not in str(p.get("name", "")).upper()]
    if not main:
        ok, msg = wake_qq_app(adb)
        _emit({"type": "log", "text": msg})
        time.sleep(2.5)
        procs = list_qq_procs_adb(adb)

    found: list[tuple[int, str]] = []
    for p in procs:
        found.append((int(p["pid"]), str(p["name"])))

    def rank(item: tuple[int, str]) -> tuple[int, str]:
        n = item[1]
        if ":MSF" in n.upper():
            return (0, n)
        if n == QQ_PKG:
            return (1, n)
        return (2, n)

    found.sort(key=rank)
    if not found:
        raise RuntimeError("未找到 QQ 进程，请打开 QQ 并停在验证码页")
    return found


def _qq_targets_frida(device) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for proc in device.enumerate_processes():
        name = proc.name or ""
        if QQ_PKG not in name:
            continue
        found.append((int(proc.pid), name))

    def rank(item: tuple[int, str]) -> tuple[int, str]:
        n = item[1]
        if ":MSF" in n.upper():
            return (0, n)
        if n == QQ_PKG:
            return (1, n)
        return (2, n)

    found.sort(key=rank)
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
                if re_is_hex(hex_data):
                    result = parser_mod.parse_auto(bytes.fromhex(hex_data))
                    if result.accounts:
                        qq = result.accounts[0].key_uin
            except (ValueError, TypeError):
                pass
        _emit({"type": "tlv", "hex": hex_data, "qq": qq, "key": payload.get("key")})


def re_is_hex(s: str) -> bool:
    if not s or len(s) % 2:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def _inject_one(device, parser_mod, hook_source: str, pid: int, name: str) -> bool:
    prefix = "var __HOOK_MODE__ = 'keyonly';\nvar __JAVA_WAIT_SEC__ = 120;\n"
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

    _SESSIONS.append({"session": session, "script": script, "pid": pid, "name": name})
    _emit({"type": "injected", "pid": pid, "name": name})
    return True


def cmd_inject(ns: argparse.Namespace) -> int:
    import frida
    from qq_bind_client import parse_qq_bind_uin as parser_mod
    from qq_bind_client.adb_helper import check_frida_version, find_frida_server
    from qq_bind_client.config import load_config

    parser_mod.run_self_test()
    _emit({"type": "log", "text": f"frida-worker {frida.__version__}"})

    cfg = load_config()
    server = find_frida_server(cfg.get("frida_server_path", ""))
    if server:
        ok, msg = check_frida_version(server)
        _emit({"type": "log", "text": msg})
        if not ok:
            raise RuntimeError(msg)

    device = frida.get_usb_device(timeout=12)
    hook_source = _hook_source()

    adb = _adb_path(ns)
    if adb:
        targets = _qq_targets_from_adb(adb)
    else:
        targets = _qq_targets_frida(device)
        if not targets:
            raise RuntimeError("未找到 QQ 进程，请打开 QQ 并停在验证码页")

    names = ", ".join(f"{n}:{p}" for p, n in targets)
    _emit({"type": "log", "text": f"QQ 进程: {names}"})

    injected = 0
    for pid, name in targets[:5]:
        if _inject_one(device, parser_mod, hook_source, pid, name):
            injected += 1

    if injected == 0:
        raise RuntimeError("所有进程注入失败。请开 USB调试(安全设置)，并在 Magisk 授权 Shell/ADB")

    _emit({"type": "log", "text": f"已注入 {injected} 个进程 — 请立刻填验证码并提交"})
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    return 0


def cmd_diagnose(ns: argparse.Namespace) -> int:
    import frida
    from qq_bind_client.adb_helper import (
        check_frida_version,
        device_abi,
        find_frida_server,
        frida_check_connection,
        frida_server_running,
        list_devices,
        list_qq_procs_adb,
        read_phone_prop,
    )
    from qq_bind_client.config import load_config

    _emit({"type": "log", "text": f"frida-python {frida.__version__}"})

    adb = _adb_path(ns)
    if adb:
        devs = list_devices(adb)
        if not devs:
            _emit({"type": "log", "text": "adb: 无设备或未授权"})
        else:
            brand = read_phone_prop(adb, "ro.product.brand")
            model = read_phone_prop(adb, "ro.product.model")
            abi = device_abi(adb)
            frida_on = frida_server_running(adb)
            _emit({"type": "log", "text": f"手机: {brand} {model} abi={abi} frida-server={'开' if frida_on else '关'}"})
            for p in list_qq_procs_adb(adb):
                _emit({"type": "proc", "pid": p["pid"], "name": p["name"]})
    else:
        _emit({"type": "log", "text": "adb 未配置"})

    cfg = load_config()
    server = find_frida_server(cfg.get("frida_server_path", ""))
    if server:
        ok, msg = check_frida_version(server)
        _emit({"type": "log", "text": msg})
    else:
        _emit({"type": "log", "text": "frida-server 文件未选择"})

    ok, msg = frida_check_connection()
    _emit({"type": "log", "text": msg})

    if ok:
        device = frida.get_usb_device(timeout=5)
        for pid, name in _qq_targets_frida(device):
            _emit({"type": "proc", "pid": pid, "name": name, "via": "frida"})

    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        _emit({"type": "error", "text": "missing command"})
        return 2
    ns = _parse_args(args)
    try:
        if ns.command == "inject":
            return cmd_inject(ns)
        if ns.command == "diagnose":
            return cmd_diagnose(ns)
        _emit({"type": "error", "text": f"unknown command: {ns.command}"})
        return 2
    except Exception as exc:
        _emit({"type": "error", "text": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
