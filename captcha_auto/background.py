import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from src.config import load_config
from src.detector import detect_captcha
from src.logger import log
from src.screen import grab_region
from src.solver import solve_once
from src.winutil import wegame_is_running


def main():
    cfg = load_config()
    bg = cfg.get("background_mode", True)
    interval = cfg.get("auto_interval_sec", 0.8)
    cooldown = cfg.get("cooldown_sec", 4)
    watch_app = cfg.get("watch_wegame_window", True)
    log_file = cfg.get("log_file", "captcha_auto.log")

    log("后台过码服务启动", log_file)
    log(f"检测间隔 {interval}s，过码后冷却 {cooldown}s", log_file)

    last_solve = 0.0
    last_idle_log = 0.0

    try:
        while True:
            if watch_app and not wegame_is_running():
                if time.time() - last_idle_log > 30:
                    log("等待 WeGameTQ 窗口...", log_file)
                    last_idle_log = time.time()
                time.sleep(2)
                continue

            frame = grab_region(cfg["region"])
            found, reason = detect_captcha(frame, cfg.get("motion", {}))

            if found and (time.time() - last_solve) >= cooldown:
                log(f"检测到验证码 ({reason})，开始过码...", log_file)
                ok, msg = solve_once(cfg)
                if ok:
                    log(f"过码成功: {msg}", log_file)
                    last_solve = time.time()
                else:
                    log(f"过码失败: {msg}", log_file)
                    last_solve = time.time() - cooldown + 1.5

            time.sleep(interval)
    except KeyboardInterrupt:
        log("后台服务已停止", log_file)


if __name__ == "__main__":
    main()
