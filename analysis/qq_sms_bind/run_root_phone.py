#!/usr/bin/env python3
"""
Root 手机一键 Hook QQ 短信查绑流程。

前置：
  - 手机已 Root，USB 调试开启
  - 已安装 QQ（com.tencent.mobileqq）
  - 电脑: pip install frida frida-tools
  - 手机: 运行与电脑 frida 同版本的 frida-server

用法：
  python3 run_root_phone.py              # USB 附加已打开的 QQ
  python3 run_root_phone.py --spawn      # 冷启动 QQ 并注入
  python3 run_root_phone.py --device ID  # 指定 frida 设备

操作：
  1. 运行本脚本
  2. 在手机上打开 QQ → 手机号登录/找回 → 输入测试手机号
  3. 收到短信后输入验证码
  4. 终端会打印 plain_qq 或 tlv543 hex
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
HOOK_JS = SCRIPT_DIR / "frida_hook.js"
QQ_PKG = "com.tencent.mobileqq"


def import_parser():
    import importlib.util

    spec = importlib.util.spec_from_file_location("parse_qq_bind_uin", SCRIPT_DIR / "parse_qq_bind_uin.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def on_message(parser, message):
    if message["type"] == "send":
        payload = message.get("payload") or {}
        kind = payload.get("type")
        if kind == "plain_qq":
            qq = payload.get("qq")
            print(f"\n>>> 明文 QQ: {qq}  (来源: {payload.get('source')})\n")
            return
        if kind == "tlv543":
            hex_data = (payload.get("hex") or "").replace(" ", "")
            print(f"\n>>> 捕获 TLV543 key={payload.get('key')} hex_len={len(hex_data)//2}")
            if hex_data:
                try:
                    raw = bytes.fromhex(hex_data)
                    result = parser.parse_auto(raw)
                    for acc in result.accounts:
                        print(f"    解析 QQ: {acc.key_uin} ({result.parse_path})")
                    if not result.accounts:
                        print("    (未能从 hex 解析 QQ，已保存 hex 可手动 parse)")
                    print(f"    hex: {hex_data[:120]}{'...' if len(hex_data)>120 else ''}\n")
                except ValueError as exc:
                    print(f"    hex 解析失败: {exc}\n")
            return
        if kind == "log":
            print(f"[frida] {payload.get('msg')}")
    elif message["type"] == "error":
        print(f"[frida-error] {message.get('stack') or message}", file=sys.stderr)


def main() -> int:
    parser_mod = import_parser()
    parser_mod.run_self_test()

    try:
        import frida
    except ImportError:
        print("请先安装: pip install frida frida-tools", file=sys.stderr)
        return 1

    if not HOOK_JS.exists():
        print(f"缺少 {HOOK_JS}", file=sys.stderr)
        return 1

    ap = argparse.ArgumentParser(description="Root 手机 Hook QQ 短信查绑")
    ap.add_argument("--spawn", action="store_true", help="冷启动 QQ")
    ap.add_argument("--device", help="frida 设备 id (frida-ls-devices 查看)")
    ap.add_argument("--process", default="", help="进程名，默认依次尝试 QQ 主进程和 :MSF")
    args = ap.parse_args()

    hook_source = HOOK_JS.read_text(encoding="utf-8")
    device = frida.get_device(args.device) if args.device else frida.get_usb_device(timeout=10)

    print(f"[*] 设备: {device.name}")
    if args.spawn:
        print(f"[*] 冷启动 {QQ_PKG} ...")
        pid = device.spawn([QQ_PKG])
        session = device.attach(pid)
        script = session.create_script(hook_source)
        script.on("message", lambda m, d: on_message(parser_mod, m))
        script.load()
        device.resume(pid)
    else:
        targets = [args.process] if args.process else [QQ_PKG, QQ_PKG + ":MSF"]
        session = None
        last_err = None
        for target in targets:
            if not target:
                continue
            try:
                session = device.attach(target)
                print(f"[*] 已附加进程: {target}")
                break
            except frida.ProcessNotFoundError as exc:
                last_err = exc
        if session is None:
            print(f"未找到 QQ 进程，尝试过: {targets}", file=sys.stderr)
            print("请先打开 QQ，或使用 --spawn / --process com.tencent.mobileqq:MSF", file=sys.stderr)
            return 1
        script = session.create_script(hook_source)
        script.on("message", lambda m, d: on_message(parser_mod, m))
        script.load()

    print("[*] Hook 已注入。请在 QQ 里走：手机号 → 收短信 → 填验证码")
    print("[*] Ctrl+C 退出\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] 退出")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
