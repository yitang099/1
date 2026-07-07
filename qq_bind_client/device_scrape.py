"""填完验证码后从手机 QQ 数据目录抓取明文 QQ。"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from qq_bind_client.config import results_dir

QQ_PKG = "com.tencent.mobileqq"

QQ_PATTERNS = (
    re.compile(r"str_key_uin[^0-9]{0,12}([1-9]\d{4,10})", re.I),
    re.compile(r"key_uin[^0-9]{0,12}([1-9]\d{4,10})", re.I),
    re.compile(r"keyUin[^0-9]{0,12}([1-9]\d{4,10})", re.I),
    re.compile(r'"uin"\s*:\s*"?([1-9]\d{4,10})"?', re.I),
    re.compile(r"<uin>([1-9]\d{4,10})</uin>", re.I),
    re.compile(r"\buin[=:][\s\"]*([1-9]\d{5,10})", re.I),
)

SKIP_QQ = re.compile(r"^(202[4-6]|22127|17\d{3})$")


def _valid_qq(num: str) -> bool:
    if not re.fullmatch(r"[1-9]\d{4,10}", num):
        return False
    return not SKIP_QQ.match(num)


def _run(adb: str, cmd: str, timeout: float = 45) -> str:
    try:
        p = subprocess.run(
            [adb, "shell", "su", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return (p.stdout or "") + (p.stderr or "")
    except Exception as exc:
        return f"(error: {exc})"


def _extract_from_text(text: str) -> list[str]:
    hits: list[str] = []
    for pat in QQ_PATTERNS:
        for m in pat.finditer(text):
            qq = m.group(1)
            if _valid_qq(qq):
                hits.append(qq)
    return hits


def scrape_qq_data(adb: str) -> tuple[str | None, Path | None, str]:
    """Root 读取 QQ 目录，找 key_uin / uin 字段。返回 (qq, dump_path, message)。"""
    roots = (
        f"/data/data/{QQ_PKG}",
        f"/data/user/0/{QQ_PKG}",
    )
    chunks: list[str] = []
    for root in roots:
        chunks.append(f"=== {root} ===\n")
        chunks.append(
            _run(
                adb,
                f'grep -r -a -i -E "key_uin|keyUin|str_key_uin|\\buin" {root}/shared_prefs {root}/files 2>/dev/null | head -80',
                timeout=60,
            )
        )
        chunks.append(
            _run(
                adb,
                f'find {root}/shared_prefs -name "*.xml" -exec grep -a -H -E "uin|Uin" {{}} \\; 2>/dev/null | head -40',
                timeout=45,
            )
        )

    text = "\n".join(chunks)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_path = results_dir() / f"device_scrape_{ts}.txt"
    try:
        dump_path.write_text(text or "(empty)", encoding="utf-8")
    except OSError:
        dump_path = None

    strict: list[str] = []
    loose: list[str] = []
    for line in text.splitlines():
        for qq in _extract_from_text(line):
            if "key_uin" in line.lower() or "keyuin" in line.lower() or "str_key_uin" in line.lower():
                strict.append(qq)
            else:
                loose.append(qq)

    if strict:
        qq = strict[-1]
        return qq, dump_path, f"设备文件 key_uin 字段: {qq}"
    if loose:
        from collections import Counter

        qq = Counter(loose).most_common(1)[0][0]
        return qq, dump_path, f"设备文件 uin 相关: {qq}（请核对）"
    msg = "设备目录未找到 QQ 号"
    if dump_path:
        msg += f"，原始数据: {dump_path.name}"
    return None, dump_path, msg
