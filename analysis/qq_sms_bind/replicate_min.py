#!/usr/bin/env python3
"""
Minimal replication entry for QQ SMS bind -> plain QQ (keyUin).

What this replicates
--------------------
1. Parser: TLV 0x543 / wtlogin RspBody protobuf -> plain_qq (no device needed)
2. Hook runner: Frida inject QQ :MSF + frida_hook.js (needs Root cloud phone)
3. Logcat fallback: grep str_key_uin from adb logcat (no Java hook)

What this does NOT replicate
----------------------------
- No public HTTP API. Tencent only returns key_uin inside QQ app after SMS verify.
- Cannot skip real SMS + QQ client. Must run com.tencent.mobileqq on Android.

Quick start
-----------
  # 1) verify parser (offline)
  python3 replicate_min.py test-parser

  # 2) full hook (ADB connected, QQ on login page, frida-server running)
  python3 replicate_min.py hook --adb 127.0.0.1:28862

  # 3) parse captured hex dump
  python3 replicate_min.py parse --hex <hex> [--json]

Protocol (TLV543 body)
----------------------
RspBody
  field 650  msg_rsp_cmd_18
    field 82  msg_rsp_phone_sms_extend_login
      field 82  rpt_bind_uin_info[]  -> UinInfo
        field 10  str_mask_uin
        field 18  str_nick
        field 42  str_key_uin   <-- plain QQ
        field 34  bytes_encrypt_uin
        field 50  bytes_a1_sig

Hook targets (frida_hook.js)
----------------------------
- WUserSigInfo.loginResultTLVMap.get(1347)  # TLV 0x543
- wtlogin parsers (WUserSigInfo, int scene) -> AccountList.getKeyUin()
- com.tencent.mobileqq.bean.AccountInfo.<init>
- HashMap.put key=1347, OkHttp ResponseBody.string JSON sniff
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FRIDA_VER = "17.13.0"


def _import_parser():
    import importlib.util

    name = "parse_qq_bind_uin"
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / "parse_qq_bind_uin.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def cmd_test_parser() -> int:
    mod = _import_parser()
    mod.run_self_test()
    raw = mod.build_self_test_payload()
    print(f"\nself-test payload hex ({len(raw)} bytes):")
    print(raw.hex())
    return 0


def cmd_parse(hex_str: str, as_json: bool) -> int:
    mod = _import_parser()
    cleaned = re.sub(r"\s+", "", hex_str)
    raw = mod.normalize_input(bytes.fromhex(cleaned))
    result = mod.parse_auto(raw)
    if as_json:
        print(
            json.dumps(
                {
                    "parse_path": result.parse_path,
                    "source": result.source,
                    "accounts": [
                        {
                            "plain_qq": a.key_uin,
                            "mask_uin": a.mask_uin,
                            "nick": a.nick,
                        }
                        for a in result.accounts
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        mod.print_human(result)
    return 0 if result.accounts else 2


def cmd_logcat(adb: str) -> int:
    sys.path.insert(0, str(SCRIPT_DIR))
    import device_setup as ds
    import qq_easy_core as core

    plain = core.logcat_plain(adb, clear_first=True)
    if plain:
        print(json.dumps({"plain_qq": plain, "source": "logcat"}, ensure_ascii=False))
        return 0
    print("no plain_qq in logcat", file=sys.stderr)
    return 1


def cmd_hook(adb: str | None, spawn: bool) -> int:
    try:
        import frida  # noqa: F401
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", f"frida=={FRIDA_VER}", "-q"]
        )
    sys.path.insert(0, str(SCRIPT_DIR))
    import device_setup as ds
    from auto_run import Collector, attach_with_recovery, load_parser_module, on_message

    hook_js = (SCRIPT_DIR / "frida_hook.js").read_text(encoding="utf-8")
    parser = load_parser_module()
    collector = Collector(parser, json_out=True)

    adb_path = adb or ds.find_adb()
    if not adb_path:
        raise SystemExit("adb not found; install platform-tools or pass --adb HOST:PORT")

    if adb:
        cfg = ds.load_config()
        cfg["adb"] = adb
        ds.save_config(cfg)
        if not ds.has_adb_device(adb_path):
            ok, msg = ds.adb_connect(adb_path, adb)
            if not ok:
                raise SystemExit(msg)

    ds.ensure_frida_python()
    ds.ensure_frida_for_hook(adb_path)
    ds.adb_bring_qq_foreground(adb_path)
    print("[*] Injecting frida_hook.js into QQ (keep QQ on SMS verify page)...", flush=True)

    sessions, device = attach_with_recovery(
        hook_js,
        collector,
        "com.tencent.mobileqq",
        spawn=spawn,
        device_arg=None,
        max_targets=1,
    )
    print("[*] Hook running. Complete SMS verify in QQ. Ctrl+C to stop.", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    for s in sessions:
        try:
            s.script.unload()
            s.session.detach()
        except Exception:
            pass
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Minimal QQ SMS bind replicator")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("test-parser", help="offline protobuf parser self-test")

    pp = sub.add_parser("parse", help="parse TLV543 / RspBody hex")
    pp.add_argument("--hex", required=True)
    pp.add_argument("--json", action="store_true")

    pl = sub.add_parser("logcat", help="grep plain QQ from adb logcat")
    pl.add_argument("--adb", default="adb")

    ph = sub.add_parser("hook", help="inject frida_hook.js into QQ")
    ph.add_argument("--adb", help="e.g. 127.0.0.1:28862 (Duoduo cloud)")
    ph.add_argument("--spawn", action="store_true", help="cold start QQ with hook")

    args = p.parse_args()
    if args.cmd == "test-parser":
        return cmd_test_parser()
    if args.cmd == "parse":
        return cmd_parse(args.hex, args.json)
    if args.cmd == "logcat":
        return cmd_logcat(args.adb)
    if args.cmd == "hook":
        return cmd_hook(args.adb, args.spawn)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
