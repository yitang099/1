#!/usr/bin/env python3
"""独立子进程运行 Frida，避免 GUI 卡死。"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

QQ_PKG = "com.tencent.mobileqq"
MSF_NAME = QQ_PKG + ":MSF"
WATCH_SEC = 180

_SESSIONS: list = []
_INJECTED: set[int] = set()


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


def _rank(name: str) -> tuple[int, str]:
    if ":MSF" in name.upper():
        return (0, name)
    if name == QQ_PKG:
        return (1, name)
    return (2, name)


def _collect_targets(adb: str | None, device) -> list[tuple[int, str]]:
    found: dict[int, str] = {}

    if adb:
        from qq_bind_client.adb_helper import list_qq_procs_adb

        for p in list_qq_procs_adb(adb):
            found[int(p["pid"])] = str(p["name"])

    for proc in device.enumerate_processes():
        name = proc.name or ""
        if QQ_PKG in name:
            found[int(proc.pid)] = name

    items = sorted(found.items(), key=lambda x: _rank(x[1]))
    return items


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
        qq = _parse_tlv_hex(parser_mod, hex_data)
        _emit({"type": "tlv", "hex": hex_data, "qq": qq, "key": payload.get("key")})


def _parse_tlv_hex(parser_mod, hex_data: str) -> str:
    if not hex_data:
        return ""
    if _is_hex(hex_data):
        try:
            result = parser_mod.parse_auto(bytes.fromhex(hex_data))
            if result.accounts:
                return result.accounts[0].key_uin
        except (ValueError, TypeError):
            pass
    m = re.search(r"([1-9]\d{4,10})", hex_data)
    return m.group(1) if m else ""


def _is_hex(s: str) -> bool:
    if not s or len(s) % 2:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def _inject_one(device, parser_mod, hook_source: str, pid: int, name: str) -> bool:
    if pid in _INJECTED:
        return False
    prefix = "var __HOOK_MODE__ = 'full';\nvar __JAVA_WAIT_SEC__ = 120;\n"
    try:
        session = device.attach(pid)
    except Exception as exc:
        _emit({"type": "log", "text": f"attach fail {name} pid={pid}: {exc}"})
        return False

    script = session.create_script(prefix + hook_source)
    script.on("message", lambda m, d, p=parser_mod: _on_frida_message(m, d, p))
    try:
        script.load()
    except Exception as exc:
        _emit({"type": "log", "text": f"load fail {name} pid={pid}: {exc}"})
        try:
            session.detach()
        except Exception:
            pass
        return False

    _SESSIONS.append({"session": session, "script": script, "pid": pid, "name": name})
    _INJECTED.add(pid)
    _emit({"type": "injected", "pid": pid, "name": name})
    return True


def _inject_by_name(device, parser_mod, hook_source: str, name: str) -> bool:
    try:
        session = device.attach(name)
    except Exception as exc:
        _emit({"type": "log", "text": f"attach by name {name}: {exc}"})
        return False
    pid = int(session.pid) if hasattr(session, "pid") else -1
    if pid > 0 and pid in _INJECTED:
        return False
    script = session.create_script(
        "var __HOOK_MODE__ = 'full';\nvar __JAVA_WAIT_SEC__ = 120;\n" + hook_source
    )
    script.on("message", lambda m, d, p=parser_mod: _on_frida_message(m, d, p))
    try:
        script.load()
    except Exception as exc:
        _emit({"type": "log", "text": f"load by name {name}: {exc}"})
        return False
    real_pid = pid if pid > 0 else 0
    _SESSIONS.append({"session": session, "script": script, "pid": real_pid, "name": name})
    if real_pid:
        _INJECTED.add(real_pid)
    _emit({"type": "injected", "pid": real_pid, "name": name})
    return True


def _inject_all(device, parser_mod, hook_source: str, targets: list[tuple[int, str]]) -> int:
    n = 0
    injected_names: set[str] = set()
    for pid, name in targets:
        if _inject_one(device, parser_mod, hook_source, pid, name):
            n += 1
            injected_names.add(name)
    for name in (MSF_NAME, QQ_PKG):
        if name in injected_names:
            continue
        already = any(n == name for _, n in targets if n == name)
        if already:
            continue
        if _inject_by_name(device, parser_mod, hook_source, name):
            n += 1
    return n


def cmd_inject(ns: argparse.Namespace) -> int:
    import frida
    from qq_bind_client import parse_qq_bind_uin as parser_mod
    from qq_bind_client.adb_helper import ensure_frida_server
    from qq_bind_client.config import load_config

    parser_mod.run_self_test()
    _emit({"type": "log", "text": f"frida-worker {frida.__version__}"})

    cfg = load_config()
    adb = _adb_path(ns)
    if adb:
        status, warn = ensure_frida_server(adb, cfg.get("frida_server_path", ""))
        _emit({"type": "log", "text": status})
        if warn:
            _emit({"type": "log", "text": f"WARN: {warn}"})

    device = frida.get_usb_device(timeout=12)
    hook_source = _hook_source()
    targets = _collect_targets(adb, device)
    if not targets:
        raise RuntimeError("no QQ process — open QQ on SMS code page")

    names = ", ".join(f"{n}:{p}" for p, n in targets)
    _emit({"type": "log", "text": f"QQ procs: {names}"})

    injected = _inject_all(device, parser_mod, hook_source, targets)
    if injected == 0:
        raise RuntimeError("inject failed — enable USB debug (security) + Magisk root")

    _emit({"type": "log", "text": f"injected {injected} — fill SMS code NOW"})
    _emit({"type": "log", "text": "watching new QQ procs (incl :MSF) for 3min..."})

    last_scan = 0.0
    try:
        while True:
            time.sleep(0.5)
            if time.time() - last_scan < 3:
                continue
            last_scan = time.time()
            for pid, name in _collect_targets(adb, device):
                if pid in _INJECTED:
                    continue
                if _inject_one(device, parser_mod, hook_source, pid, name):
                    _emit({"type": "log", "text": f"late inject {name} pid={pid}"})
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
            _emit({"type": "log", "text": "adb: no device"})
        else:
            brand = read_phone_prop(adb, "ro.product.brand")
            model = read_phone_prop(adb, "ro.product.model")
            abi = device_abi(adb)
            frida_on = frida_server_running(adb)
            _emit({"type": "log", "text": f"phone: {brand} {model} abi={abi} frida={'on' if frida_on else 'off'}"})
            for p in list_qq_procs_adb(adb):
                _emit({"type": "proc", "pid": p["pid"], "name": p["name"]})
    cfg = load_config()
    server = find_frida_server(cfg.get("frida_server_path", ""))
    if server:
        can, msg, warn = check_frida_version(server)
        _emit({"type": "log", "text": msg})
        if warn:
            _emit({"type": "log", "text": f"WARN: {warn}"})
    ok, msg = frida_check_connection()
    _emit({"type": "log", "text": msg})
    if ok:
        device = frida.get_usb_device(timeout=5)
        for pid, name in _collect_targets(adb, device):
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
