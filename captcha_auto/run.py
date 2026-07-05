import os
import sys
import time

import keyboard

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from src.config import load_config
from src.solver import solve_once


def main():
    cfg = load_config()
    hotkey = cfg.get("hotkey", "f8").lower()
    auto = cfg.get("auto_mode", False)
    interval = cfg.get("auto_interval_sec", 1.5)

    print("=" * 50)
    print(" WeGameTQ 第三方验证码助手")
    print("=" * 50)
    print()
    print(f" 验证码区域: {cfg['region']}")
    print(f" 打码账号: {cfg['api'].get('username', '(未配置)')}")
    print()
    if auto:
        print(f" [自动模式] 每 {interval}s 检测并尝试过码")
    else:
        print(f" [手动模式] 验证码出现后按 [{hotkey.upper()}] 过码")
        print("  按 [F9] 强制按【选图】处理")
        print("  按 [F10] 强制按【动态点选】处理")
    print("  按 [ESC] 退出")
    print()

    running = True

    def on_esc():
        nonlocal running
        running = False

    keyboard.add_hotkey("esc", on_esc)

    if not auto:
        def on_f8():
            ok, msg = solve_once(cfg)
            print(f"[{time.strftime('%H:%M:%S')}] F8 -> {'成功' if ok else '失败'}: {msg}")

        def on_f9():
            ok, msg = solve_once(cfg, force_type="image")
            print(f"[{time.strftime('%H:%M:%S')}] F9选图 -> {'成功' if ok else '失败'}: {msg}")

        def on_f10():
            ok, msg = solve_once(cfg, force_type="motion")
            print(f"[{time.strftime('%H:%M:%S')}] F10动态 -> {'成功' if ok else '失败'}: {msg}")

        keyboard.add_hotkey(hotkey, on_f8)
        keyboard.add_hotkey("f9", on_f9)
        keyboard.add_hotkey("f10", on_f10)

    try:
        while running:
            if auto:
                ok, msg = solve_once(cfg)
                if ok:
                    print(f"[{time.strftime('%H:%M:%S')}] 自动过码成功: {msg}")
                time.sleep(interval)
            else:
                time.sleep(0.2)
    except KeyboardInterrupt:
        pass

    print("已退出")


if __name__ == "__main__":
    main()
