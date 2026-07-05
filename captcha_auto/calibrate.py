import json
import os
import shutil
import sys
import time

import pyautogui

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from src.config import EXAMPLE_PATH, CONFIG_PATH, save_config


def main():
    print("=" * 50)
    print(" 验证码区域校准")
    print("=" * 50)
    print()
    print("步骤 1/2: 把鼠标移到验证码【左上角】，5 秒后记录...")
    time.sleep(5)
    x1, y1 = pyautogui.position()
    print(f"  左上角: ({x1}, {y1})")

    print()
    print("步骤 2/2: 把鼠标移到验证码【右下角】，5 秒后记录...")
    time.sleep(5)
    x2, y2 = pyautogui.position()
    print(f"  右下角: ({x2}, {y2})")

    width = max(50, x2 - x1)
    height = max(50, y2 - y1)

    print()
    print("步骤 3/3: 把鼠标移到【确定】按钮中心，5 秒后记录...")
    time.sleep(5)
    bx, by = pyautogui.position()
    print(f"  确定按钮: ({bx}, {by})")

    if not os.path.isfile(CONFIG_PATH):
        shutil.copy(EXAMPLE_PATH, CONFIG_PATH)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    cfg["region"] = {
        "left": x1,
        "top": y1,
        "width": width,
        "height": height,
    }
    cfg["confirm_button"] = {
        "offset_x": (x1 + width) - bx,
        "offset_y": by - y1,
    }
    save_config(cfg)

    print()
    print("校准完成，已写入 config.json")
    print(f"  region: left={x1} top={y1} width={width} height={height}")
    print(f"  confirm offset: x={cfg['confirm_button']['offset_x']} y={cfg['confirm_button']['offset_y']}")
    input("\n按回车退出...")


if __name__ == "__main__":
    main()
