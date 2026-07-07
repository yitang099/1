"""Logcat fallback QQ capture — strict + post-SMS dump."""
from __future__ import annotations

import re
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from qq_bind_client.config import results_dir

STRICT_QQ_RES = (
    re.compile(r"str_key_uin[^0-9]{0,8}([1-9]\d{4,10})", re.I),
    re.compile(r"key_uin[^0-9]{0,8}([1-9]\d{4,10})", re.I),
    re.compile(r"keyUin[^0-9]{0,8}([1-9]\d{4,10})", re.I),
    re.compile(r"getKeyUin[^0-9]{0,8}([1-9]\d{4,10})", re.I),
    re.compile(r"plain_qq[^0-9]{0,8}([1-9]\d{4,10})", re.I),
    re.compile(r"tlv[^0-9]{0,6}543[^0-9]{0,12}([1-9]\d{4,10})", re.I),
)

MEDIUM_LINE_HINTS = (
    "wtlogin",
    "WtLogin",
    "smslogin",
    "SmsLogin",
    "sms_login",
    "bind",
    "login",
    "tlv543",
    "0x543",
    "key_uin",
    "keyUin",
)

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
    "friend_list",
    "group_id",
    "qzone",
    "22127RK46C",
    "17.15.",
    "meminfo",
)


def _valid_qq(num: str) -> bool:
    if not re.fullmatch(r"[1-9]\d{4,10}", num):
        return False
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
        if m and _valid_qq(m.group(1)):
            return m.group(1)
    return None


def extract_qq_medium(line: str) -> str | None:
    if any(h in line for h in SKIP_LINE_HINTS):
        return None
    if not any(h in line for h in MEDIUM_LINE_HINTS):
        return None
    m = re.search(r"uin[^0-9]{0,12}([1-9]\d{5,10})", line, re.I)
    if m and _valid_qq(m.group(1)):
        return m.group(1)
    return None


def _qq_pids(adb: str) -> list[str]:
    try:
        p = subprocess.run(
            [adb, "shell", "pidof", "com.tencent.mobileqq"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return [x for x in (p.stdout or "").split() if x.isdigit()]
    except Exception:
        return []


def _read_logcat(adb: str) -> str:
    pids = _qq_pids(adb)
    chunks: list[str] = []
    if pids:
        for pid in pids[:4]:
            try:
                p = subprocess.run(
                    [adb, "logcat", "-d", "-v", "threadtime", f"--pid={pid}"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    encoding="utf-8",
                    errors="replace",
                )
                if p.stdout:
                    chunks.append(p.stdout)
            except Exception:
                pass
    if chunks:
        return "\n".join(chunks)
    try:
        p = subprocess.run(
            [adb, "logcat", "-d", "-v", "threadtime"],
            capture_output=True,
            text=True,
            timeout=45,
            encoding="utf-8",
            errors="replace",
        )
        text = p.stdout or ""
        lines = [ln for ln in text.splitlines() if "mobileqq" in ln or "tencent" in ln.lower() or "uin" in ln.lower()]
        return "\n".join(lines)
    except Exception:
        return ""


def dump_and_parse(adb: str) -> tuple[str | None, Path | None, str]:
    """验证码提交后一次性抓取 logcat 并解析。返回 (qq, dump_path, message)。"""
    text = _read_logcat(adb)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_path = results_dir() / f"logcat_{ts}.txt"
    try:
        dump_path.write_text(text or "(empty)", encoding="utf-8")
    except OSError:
        dump_path = None

    strict_hits: list[str] = []
    medium_hits: list[str] = []
    for line in (text or "").splitlines():
        s = extract_qq_strict(line)
        if s:
            strict_hits.append(s)
            continue
        m = extract_qq_medium(line)
        if m:
            medium_hits.append(m)

    if strict_hits:
        qq = strict_hits[-1]
        return qq, dump_path, f"严格匹配 key_uin 字段: {qq}"
    if medium_hits:
        from collections import Counter

        qq = Counter(medium_hits).most_common(1)[0][0]
        return qq, dump_path, f"登录相关日志最常见号码: {qq}（请人工核对）"
    msg = "未解析到 QQ 号"
    if dump_path:
        msg += f"，原始日志已保存: {dump_path.name}"
    return None, dump_path, msg


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

    def _maybe_emit(self, qq: str, line: str, *, need: int) -> None:
        self._hits[qq] = self._hits.get(qq, 0) + 1
        if self._hits[qq] < need:
            self._log(f"logcat 候选 x{self._hits[qq]}/{need}: {qq}")
            return
        if qq in self._seen:
            return
        self._seen.add(qq)
        self._log(f"logcat 确认 QQ: {qq}  ← {line.strip()[:100]}")
        self.on_qq(qq)

    def _run(self, adb: str) -> None:
        self._log("logcat 监听中（填完验证码后请点「验证码后抓取」更可靠）")
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
                self._maybe_emit(qq, line, need=1)
                continue
            qq = extract_qq_medium(line)
            if qq:
                self._maybe_emit(qq, line, need=3)
        try:
            proc.terminate()
        except Exception:
            pass
