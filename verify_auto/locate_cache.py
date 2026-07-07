"""定位缓存（默认不后台轮询，避免 CPU 飙高）。"""
from __future__ import annotations

import threading
import time
from typing import Any

from slider_solver.screen_match import Region

CACHE_TTL_SEC = 25.0
SEARCH_PAD = 140
LOCATE_MIN_INTERVAL = 10.0

_lock = threading.Lock()
_cache: dict[str, Any] = {"ts": 0.0, "result": None, "window": None}
_last_full_locate = 0.0
_prefetch_stop = threading.Event()
_prefetch_thread: threading.Thread | None = None


def get_cached(*, max_age: float = CACHE_TTL_SEC) -> Any | None:
    with _lock:
        result = _cache.get("result")
        if not result or not getattr(result, "ok", False):
            return None
        if time.time() - float(_cache.get("ts") or 0) > max_age:
            return None
        return result


def put_cache(result: Any) -> None:
    if not getattr(result, "ok", False) or not getattr(result, "regions", None):
        return
    with _lock:
        _cache["ts"] = time.time()
        _cache["result"] = result
        _cache["window"] = result.regions.search


def invalidate_cache() -> None:
    with _lock:
        _cache["ts"] = 0.0
        _cache["result"] = None
        _cache["window"] = None


def cached_window_region() -> Region | None:
    with _lock:
        w = _cache.get("window")
        return w if isinstance(w, Region) else None


def should_full_locate() -> bool:
    global _last_full_locate
    now = time.time()
    if now - _last_full_locate >= LOCATE_MIN_INTERVAL:
        _last_full_locate = now
        return True
    return False


def mark_full_locate() -> None:
    global _last_full_locate
    _last_full_locate = time.time()


def start_prefetch(cfg_supplier, *, enabled: bool = False, interval_sec: float = 12.0) -> None:
    """默认关闭。仅 cfg 显式 enable_prefetch=true 时可选开启。"""
    global _prefetch_thread
    stop_prefetch()
    if not enabled:
        return
    _prefetch_stop.clear()

    def loop() -> None:
        while not _prefetch_stop.wait(interval_sec):
            try:
                cfg = cfg_supplier()
                if not cfg.get("layout_profile"):
                    continue
                if not should_full_locate():
                    continue
                from verify_auto.region_resolve import resolve_regions

                resolve_regions(cfg, step_hint=0, force_refresh=True)
            except Exception:
                pass

    _prefetch_thread = threading.Thread(target=loop, daemon=True, name="locate-prefetch")
    _prefetch_thread.start()


def stop_prefetch() -> None:
    _prefetch_stop.set()
