"""Logcat fallback QQ capture when Frida Java hook unavailable."""
from __future__ import annotations

import re
import subprocess
import threading
import time
from typing import Callable

QQ_RE = re.compile(r"\b([1-9]\d{4,10})\b")
KEY_PATTERNS = ("str_key_uin", "key_uin", "keyUin", "getKeyUin", "plain_qq", "1347", "tlv")


class LogcatWatcher:
    def __init__(self, on_qq: Callable[[str], None], on_log: Callable[[str], None] | None = None) -> None:
        self.on_qq = on_qq
        self.on_log = on_log
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._seen: set[str] = set()

    def start(self, adb: str) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, args=(adb,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _log(self, msg: str) -> None:
        if self.on_log:
            self.on_log(msg)

    def _run(self, adb: str) -> None:
        self._log("logcat 备用监听已启动（完成短信验证后自动抓 QQ 号）")
        subprocess.run([adb, "logcat", "-c"], capture_output=True, timeout=10)
        try:
            proc = subprocess.Popen(
                [adb, "logcat", "-v", "brief"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            self._log(f"logcat 启动失败: {exc}")
            return
        assert proc.stdout
        while not self._stop.is_set():
            line = proc.stdout.readline()
            if not line:
                time.sleep(0.2)
                continue
            if not any(k in line for k in KEY_PATTERNS):
                continue
            for m in QQ_RE.finditer(line):
                qq = m.group(1)
                if qq in self._seen:
                    continue
                self._seen.add(qq)
                self._log(f"logcat 捕获 QQ: {qq}")
                self.on_qq(qq)
        try:
            proc.terminate()
        except Exception:
            pass
