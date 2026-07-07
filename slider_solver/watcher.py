"""后台监听：静态匹配 或 动态识别。"""
from __future__ import annotations

import threading
import time
from typing import Callable

from slider_solver.config import load_config
from slider_solver.dynamic_solver import DynamicResult, solve_dynamic
from slider_solver.records import match_record
from slider_solver.replay import ReplayResult, replay_hit
from slider_solver.screen_match import Region


class BackgroundWatcher:
    def __init__(
        self,
        on_log: Callable[[str], None] | None = None,
        on_replay: Callable[[ReplayResult], None] | None = None,
        on_dynamic: Callable[[DynamicResult], None] | None = None,
    ) -> None:
        self.on_log = on_log
        self.on_replay = on_replay
        self.on_dynamic = on_dynamic
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._cooldown_until = 0.0

    def _log(self, msg: str) -> None:
        if self.on_log:
            self.on_log(msg)

    def start(self, interval_ms: int = 600) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(max(200, interval_ms) / 1000.0,),
            daemon=True,
        )
        self._thread.start()
        self._log("后台监听已启动")

    def stop(self) -> None:
        self._stop.set()
        self._log("后台监听已停止")

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and not self._stop.is_set()

    def _run(self, interval: float) -> None:
        while not self._stop.is_set():
            if time.time() < self._cooldown_until:
                time.sleep(interval)
                continue
            cfg = load_config()
            region = Region.from_dict(cfg.get("captcha_region"))
            if not region:
                time.sleep(interval)
                continue

            mode = (cfg.get("mode") or "dynamic").lower()
            if mode == "static":
                hit = match_record(region, threshold=float(cfg.get("match_threshold") or 0.88))
                if hit:
                    self._log(f"[静态] 匹配「{hit.record.name}」score={hit.score:.2f}")
                    result = replay_hit(hit, cfg)
                    if self.on_replay:
                        self.on_replay(result)
                    if result.ok:
                        self._cooldown_until = time.time() + float(cfg.get("cooldown_sec") or 3)
            else:
                # 动态：检测区域里是否像滑块（简单判断：有足够方差）
                from slider_solver.screen_match import grab_region
                import numpy as np

                img = grab_region(region)
                if float(np.std(img)) < 8:
                    time.sleep(interval)
                    continue
                result = solve_dynamic(cfg)
                if result.ok:
                    self._log(f"[动态] {result.message}")
                    if self.on_dynamic:
                        self.on_dynamic(result)
                    self._cooldown_until = time.time() + float(cfg.get("cooldown_sec") or 3)
                elif result.confidence > 0.1:
                    self._log(f"[动态] 跳过: {result.message}")

            time.sleep(interval)
