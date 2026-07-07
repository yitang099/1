"""全局快捷键 F8/F9/F10（验证码窗口在前台时也能触发）。"""
from __future__ import annotations

import threading
import time
from typing import Callable


class GlobalHotkeys:
    def __init__(self) -> None:
        self._listener = None
        self._last_ts = 0.0
        self._handlers: dict[str, Callable[[], None]] = {}

    def register(self, key_name: str, handler: Callable[[], None]) -> None:
        self._handlers[key_name.lower()] = handler

    def start(self) -> None:
        if self._listener:
            return
        try:
            from pynput import keyboard
        except ImportError:
            return

        key_map = {
            "f8": keyboard.Key.f8,
            "f9": keyboard.Key.f9,
            "f10": keyboard.Key.f10,
        }

        def on_press(key) -> None:
            now = time.time()
            if now - self._last_ts < 0.35:
                return
            for name, special in key_map.items():
                if key == special and name in self._handlers:
                    self._last_ts = now
                    self._handlers[name]()
                    return

        self._listener = keyboard.Listener(on_press=on_press)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None


_hotkeys: GlobalHotkeys | None = None
_lock = threading.Lock()


def get_hotkeys() -> GlobalHotkeys:
    global _hotkeys
    with _lock:
        if _hotkeys is None:
            _hotkeys = GlobalHotkeys()
        return _hotkeys
