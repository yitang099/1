"""Logcat fallback QQ capture — strict filters to avoid false positives."""
from __future__ import annotations

import re
import subprocess
import threading
import time
from typing import Callable

# 必须从日志字段结构中提取，不能仅靠行内任意数字
STRICT_QQ_RES = (
    re.compile(r"str_key_uin[^0-9]{0,8}([1-9]\d{4,10})", re.I),
    re.compile(r"key_uin[^0-9]{0,8}([1-9]\d{4,10})", re.I),
    re.compile(r"keyUin[^0-9]{0,8}([1-9]\d{4,10})", re.I),
    re.compile(r"getKeyUin[^0-9]{0,8}([1-9]\d{4,10})", re.I),
    re.compile(r"plain_qq[^0-9]{0,8}([1-9]\d{4,10})", re.I),
    re.compile(r"tlv[^0-9]{0,6}543[^0-9]{0,12}([1-9]\d{4,10})", re.I),
)

# 行内出现这些则整行丢弃（常见误报来源）
SKIP_LINE_HINTS = (
    "pid=",
    "port=",
    "version",
    "Build/",
    "frida",
    "http://",
    "https://",
    "recommend",
    "advert",
    "广告",
    "friend_list",
    "group_id",
    "qzone",
    "timestamps",
    "Redmi",
    "22127RK46C",
    "17.15.",
    "mobileqq:MSF",
    "process",
    "meminfo",
)


def _valid_qq(num: str) -> bool:
    if not re.fullmatch(r"[1-9]\d{4,10}", num):
        return False
    # 排除明显像年份/版本/设备号的
    if num.startswith(("2024", "2025", "2026", "22127")):
        return False
    if len(num) == 5 and num.startswith("17"):
        return False
    return True


def extract_qq_strict(line: str) -> str | None:
    if any(h in line for h in SKIP_LINE_HINTS):
        return None
    for pat in STRICT_QQ_RES:
        m = pat.search(line)
        if m:
            qq = m.group(1)
            if _valid_qq(qq):
                return qq
    return None


class LogcatWatcher:
    def __init__(self, on_qq: Callable[[str], None], on_log: Callable[[str], None] | None = None) -> None:
        self.on_qq = on_qq
        self.on_log = on_log
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._seen: set[str] = set()
        self._hits: dict[str, int] = {}

    def start(self, adb: str) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._seen.clear()
        self._hits.clear()
        self._thread = threading.Thread(target=self._run, args=(adb,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _log(self, msg: str) -> None:
        if self.on_log:
            self.on_log(msg)

    def _maybe_emit(self, qq: str, line: str) -> None:
        self._hits[qq] = self._hits.get(qq, 0) + 1
        # 同一 QQ 在严格规则下出现 2 次才确认（防单条噪声）
        if self._hits[qq] < 2:
            self._log(f"logcat 候选(待确认 x{self._hits[qq]}): {qq}")
            return
        if qq in self._seen:
            return
        self._seen.add(qq)
        snippet = line.strip()[:120]
        self._log(f"logcat 确认 QQ: {qq}  ← {snippet}")
        self.on_qq(qq)

    def _run(self, adb: str) -> None:
        self._log("logcat 严格模式（仅 key_uin/plain_qq/tlv543 字段，过滤噪声）")
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
            qq = extract_qq_strict(line)
            if qq:
                self._maybe_emit(qq, line)
        try:
            proc.terminate()
        except Exception:
            pass
