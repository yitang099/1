import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from src.config import load_config
from src.detector import detect_captcha
from src.logger import log
from src.motion_solver import looks_like_motion
from src.screen import grab_region
from src.solver import solve_once
from src.winutil import wegame_is_running


def _resolve_type(reason, frame, cfg):
    motion_cfg = cfg.get("motion", {})
    is_motion = looks_like_motion(
        frame,
        motion_cfg.get("min_area", 8),
        motion_cfg.get("max_area", 800),
    )
    if "motion" in reason and is_motion:
        return "motion"
    if "image" in reason and cfg.get("auto_image_solve") and cfg["api"].get("model_id"):
        return "image"
    if is_motion:
        return "motion"
    if cfg.get("auto_image_solve") and cfg["api"].get("model_id"):
        return "image"
    return None


def main():
    cfg = load_config()
    interval = cfg.get("auto_interval_sec", 0.8)
    cooldown = cfg.get("cooldown_sec", 4)
    watch_app = cfg.get("watch_wegame_window", True)
    log_file = cfg.get("log_file", "captcha_auto.log")

    log("后台过码服务启动", log_file)
    log(f"检测间隔 {interval}s，过码后冷却 {cooldown}s", log_file)
    if not cfg["api"].get("model_id"):
        log("提示: 未填 api.model_id，后台只自动过【动态点选】，选图请填 model_id 或手动 F9", log_file)

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
                solve_type = _resolve_type(reason, frame, cfg)
                if solve_type is None:
                    time.sleep(interval)
                    continue
                log(f"检测到验证码 ({reason})，按 {solve_type} 过码...", log_file)
                ok, msg = solve_once(cfg, force_type=solve_type, detect_reason=reason)
                if ok:
                    log(f"过码成功: {msg}", log_file)
                    last_solve = time.time()
                else:
                    log(f"过码失败: {msg}", log_file)
                    last_solve = time.time() - cooldown + 2

            time.sleep(interval)
    except KeyboardInterrupt:
        log("后台服务已停止", log_file)


if __name__ == "__main__":
    main()
