"""填完验证码后从手机 QQ 数据目录抓取明文 QQ。"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from qq_bind_client.config import results_dir

QQ_PKG = "com.tencent.mobileqq"
QQ_DATA = f"/data/user/0/{QQ_PKG}"

QQ_PATTERNS = (
    re.compile(r"str_key_uin[^0-9]{0,12}([1-9]\d{4,10})", re.I),
    re.compile(r"key_uin[^0-9]{0,12}([1-9]\d{4,10})", re.I),
    re.compile(r"keyUin[^0-9]{0,12}([1-9]\d{4,10})", re.I),
    re.compile(r"saltUin[^0-9]{0,12}([1-9]\d{4,10})", re.I),
    re.compile(r'"uin"\s*:\s*"?([1-9]\d{4,10})"?', re.I),
    re.compile(r"<uin>([1-9]\d{4,10})</uin>", re.I),
    re.compile(r"\buin[=:][\s\"]*([1-9]\d{5,10})", re.I),
)

SKIP_QQ = re.compile(r"^(202[4-6]|22127|17\d{3})$")

# 定向文件，避免全目录 grep 超时（QQ 9.2.x 账号缓存）
TARGET_GLOBS = (
    "AppUinStoreFile*",
    "AppUinBackStoreFile*",
    "*account*",
    "*uin*",
    "login*",
)


def _valid_qq(num: str) -> bool:
    if not re.fullmatch(r"[1-9]\d{4,10}", num):
        return False
    return not SKIP_QQ.match(num)


def _run(adb: str, cmd: str, timeout: float = 20) -> str:
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
    except subprocess.TimeoutExpired:
        return "(timeout)"
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


def _scrape_targeted(adb: str) -> list[str]:
    chunks: list[str] = []
    base = QQ_DATA

    chunks.append(f"=== find uin/account files under {base}/files ===\n")
    find_cmd = (
        f"find {base}/files -maxdepth 3 "
        f"\\( -iname '*Uin*' -o -iname '*account*' -o -iname 'login*' \\) "
        f"-type f 2>/dev/null | head -25"
    )
    found = _run(adb, find_cmd, timeout=15)
    chunks.append(found)

    for line in found.splitlines():
        path = line.strip()
        if not path.startswith("/"):
            continue
        chunks.append(f"\n--- strings {path} ---\n")
        chunks.append(_run(adb, f"strings {path} 2>/dev/null | head -40", timeout=12))
        chunks.append(_run(adb, f"grep -a -o -E '.{{0,20}}(key_uin|saltUin|uin).{{0,30}}' {path} 2>/dev/null | head -15", timeout=12))

    chunks.append(f"\n=== shared_prefs (quick) ===\n")
    chunks.append(
        _run(
            adb,
            f"grep -r -a -l -i -E 'uin|account' {base}/shared_prefs 2>/dev/null | head -10",
            timeout=15,
        )
    )
    prefs = [ln.strip() for ln in chunks[-1].splitlines() if ln.strip().startswith("/")]
    for pref in prefs[:6]:
        chunks.append(f"\n--- {pref} ---\n")
        chunks.append(_run(adb, f"grep -a -E 'uin|Uin|account' {pref} 2>/dev/null | head -20", timeout=10))

    chunks.append(f"\n=== MsfSdkUtils paths (logcat hint) ===\n")
    for name in ("AppUinStoreFile", "AppUinBackStoreFile", "NewAppUinStoreFile"):
        chunks.append(_run(adb, f"ls -la {base}/files/*{name}* 2>/dev/null", timeout=8))
        chunks.append(_run(adb, f"strings {base}/files/*{name}* 2>/dev/null | head -30", timeout=10))

    return chunks


def scrape_qq_data(adb: str) -> tuple[str | None, Path | None, str]:
    """Root 定向读取 QQ 账号缓存文件。返回 (qq, dump_path, message)。"""
    chunks = _scrape_targeted(adb)
    text = "\n".join(chunks)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_path = results_dir() / f"device_scrape_{ts}.txt"
    try:
        dump_path.write_text(text or "(empty)", encoding="utf-8")
    except OSError:
        dump_path = None

    strict: list[str] = []
    salt: list[str] = []
    loose: list[str] = []
    for line in text.splitlines():
        low = line.lower()
        for qq in _extract_from_text(line):
            if "key_uin" in low or "keyuin" in low or "str_key_uin" in low:
                strict.append(qq)
            elif "saltuin" in low:
                salt.append(qq)
            else:
                loose.append(qq)

    if strict:
        qq = strict[-1]
        return qq, dump_path, f"设备文件 key_uin 字段: {qq}"
    if salt:
        from collections import Counter

        qq = Counter(salt).most_common(1)[0][0]
        return qq, dump_path, f"设备文件 saltUin: {qq}（NTLogin 9.2.x）"
    if loose:
        from collections import Counter

        qq = Counter(loose).most_common(1)[0][0]
        return qq, dump_path, f"设备文件 uin 相关: {qq}（请核对）"
    msg = "设备目录未找到 QQ 号（请先在多账号弹窗点选一个 QQ）"
    if dump_path:
        msg += f"，原始数据: {dump_path.name}"
    return None, dump_path, msg
