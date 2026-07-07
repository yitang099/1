"""Detect whether QQ SMS bind uses wtlogin/TLV543 or NTLogin."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field

QQ_PKG = "com.tencent.mobileqq"

# 强特征：出现即高度可信
WTLOGIN_STRONG = (
    "oicq.wlogin_sdk",
    "WtloginHelper",
    "WUserSigInfo",
    "loginResultTLVMap",
    "wtlogin.login",
)
NTLOGIN_STRONG = (
    "SsoNTLoginCheckSms",
    "SsoNTLoginGetSms",
    "onGetSaltUinList",
    "NTLoginMainline_PhoneSmsLogin",
)

# 弱特征：需结合其它线索
WTLOGIN_WEAK = (
    "wtlogin",
    "WtLogin",
    "tlv543",
    "key_uin",
    "str_key_uin",
    "getKeyUin",
)
NTLOGIN_WEAK = (
    "[nt_login]",
    "trpc.login.ecdh",
    "saltUin",
    "showMultiAccountDialog",
)


@dataclass
class PathDetectResult:
    path: str  # wtlogin | ntlogin | unknown | mixed
    qq_version: str
    confidence: str  # high | medium | low
    wtlogin_hits: list[str] = field(default_factory=list)
    ntlogin_hits: list[str] = field(default_factory=list)
    source: str = "logcat"  # logcat | version_heuristic
    summary: str = ""
    advice: str = ""

    def lines(self) -> list[str]:
        path_cn = {
            "wtlogin": "wtlogin / TLV 543（老路）",
            "ntlogin": "NTLogin（新路）",
            "mixed": "混合/过渡（两种都有）",
            "unknown": "未知（线索不足）",
        }.get(self.path, self.path)
        conf_cn = {"high": "高", "medium": "中", "low": "低"}.get(self.confidence, self.confidence)
        out = [
            f"QQ 版本: {self.qq_version or '未知'}",
            f"短信查绑路径: {path_cn}",
            f"置信度: {conf_cn}（来源: {self.source}）",
        ]
        if self.wtlogin_hits:
            out.append("wtlogin 命中: " + ", ".join(self.wtlogin_hits[:8]))
        if self.ntlogin_hits:
            out.append("NTLogin 命中: " + ", ".join(self.ntlogin_hits[:8]))
        out.append(self.summary)
        if self.advice:
            out.append("建议: " + self.advice)
        return out


def _run(adb: str, args: list[str], timeout: float = 25) -> str:
    try:
        p = subprocess.run(
            [adb, *args],
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


def get_qq_version(adb: str) -> str:
    text = _run(adb, ["shell", "dumpsys", "package", QQ_PKG], timeout=20)
    for pat in (
        r"versionName=([^\s]+)",
        r"versionName\s*=\s*([^\s]+)",
    ):
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    # logcat 备用
    log = _read_qq_logcat(adb, lines_limit=800)
    m = re.search(r"app_vr=([0-9.]+)", log)
    if m:
        return m.group(1)
    return ""


def _qq_pids(adb: str) -> list[str]:
    out = _run(adb, ["shell", "pidof", QQ_PKG], timeout=10).strip()
    return [x for x in out.split() if x.isdigit()]


def _read_qq_logcat(adb: str, *, lines_limit: int = 4000) -> str:
    chunks: list[str] = []
    pids = _qq_pids(adb)
    if pids:
        for pid in pids[:4]:
            text = _run(
                adb,
                ["logcat", "-d", "-v", "threadtime", f"--pid={pid}"],
                timeout=30,
            )
            if text and not text.startswith("(error"):
                chunks.append(text)
    if chunks:
        merged = "\n".join(chunks)
        lines = merged.splitlines()
        if len(lines) > lines_limit:
            return "\n".join(lines[-lines_limit:])
        return merged

    text = _run(adb, ["logcat", "-d", "-v", "threadtime"], timeout=35)
    lines = [
        ln
        for ln in text.splitlines()
        if QQ_PKG in ln or "NTLogin" in ln or "wtlogin" in ln or "nt_login" in ln
    ]
    if len(lines) > lines_limit:
        lines = lines[-lines_limit:]
    return "\n".join(lines)


def _collect_hits(text: str, strong: tuple[str, ...], weak: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for s in strong:
        if s in text and s not in hits:
            hits.append(s)
    for s in weak:
        if s in text and s not in hits:
            hits.append(s)
    return hits


def _version_heuristic(version: str) -> tuple[str, str]:
    """无 logcat 线索时，仅按版本号粗判（低置信度）。"""
    if not version:
        return "unknown", "low"
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    if not m:
        return "unknown", "low"
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    ver_tuple = (major, minor, patch)
    if ver_tuple >= (9, 2, 0):
        return "ntlogin", "low"
    if ver_tuple <= (8, 9, 99):
        return "wtlogin", "low"
    return "unknown", "low"


def detect_from_logcat_text(text: str, qq_version: str = "") -> PathDetectResult:
    wt = _collect_hits(text, WTLOGIN_STRONG, WTLOGIN_WEAK)
    nt = _collect_hits(text, NTLOGIN_STRONG, NTLOGIN_WEAK)

    wt_score = sum(3 if h in WTLOGIN_STRONG else 1 for h in wt)
    nt_score = sum(3 if h in NTLOGIN_STRONG else 1 for h in nt)

    if wt_score == 0 and nt_score == 0:
        path, conf = _version_heuristic(qq_version)
        advice = _advice_for(path, has_logcat=False)
        summary = "logcat 中未发现登录协议特征（可能还没走短信验证流程）"
        if path != "unknown":
            summary += f"；按版本号 {qq_version} 粗判为 {_path_label(path)}"
        return PathDetectResult(
            path=path,
            qq_version=qq_version,
            confidence=conf,
            wtlogin_hits=wt,
            ntlogin_hits=nt,
            source="version_heuristic",
            summary=summary,
            advice=advice,
        )

    wt_strong = any(h in WTLOGIN_STRONG for h in wt)
    nt_strong = any(h in NTLOGIN_STRONG for h in nt)

    if wt_strong and nt_strong:
        path = "mixed"
        conf = "medium"
        summary = "同时出现 wtlogin 与 NTLogin 强特征，可能处于过渡期"
    elif nt_score > wt_score:
        path = "ntlogin"
        conf = "high" if nt_strong else "medium"
        summary = "检测到 NTLogin 短信登录特征（SsoNTLogin* / onGetSaltUinList）"
        if wt and not nt_strong:
            summary += f"；另有弱 wtlogin 痕迹: {', '.join(wt[:3])}"
    elif wt_score > nt_score:
        path = "wtlogin"
        conf = "high" if wt_strong else "medium"
        summary = f"检测到 wtlogin / TLV 543 特征（{', '.join(wt[:3])}）"
        if nt and not wt_strong:
            summary += f"；另有弱 NTLogin 痕迹: {', '.join(nt[:3])}"
    elif wt_score == nt_score and wt_strong:
        path = "wtlogin"
        conf = "medium"
        summary = "wtlogin 与 NTLogin 弱特征并存，按 wtlogin 处理"
    elif wt_score == nt_score and nt_strong:
        path = "ntlogin"
        conf = "medium"
        summary = "wtlogin 与 NTLogin 弱特征并存，按 NTLogin 处理"
    else:
        path = "unknown"
        conf = "low"
        summary = "线索不足，请在验证码页重新检测"

    return PathDetectResult(
        path=path,
        qq_version=qq_version,
        confidence=conf,
        wtlogin_hits=wt,
        ntlogin_hits=nt,
        source="logcat",
        summary=summary,
        advice=_advice_for(path, has_logcat=True),
    )


def _path_label(path: str) -> str:
    return {
        "wtlogin": "wtlogin / TLV 543",
        "ntlogin": "NTLogin",
        "mixed": "混合",
        "unknown": "未知",
    }.get(path, path)


def _advice_for(path: str, *, has_logcat: bool) -> str:
    if path == "wtlogin":
        return "使用现有 HashMap/TLV543 Hook；8.9.x 工具链匹配度高"
    if path == "ntlogin":
        return "使用 NTLogin Hook（onGetSaltUinList / pbBuffer）；多绑号需在列表阶段抓全部 QQ"
    if path == "mixed":
        return "优先以强特征为准；建议在验证码页重新抓一次 logcat"
    if not has_logcat:
        return "请先在 QQ 打开手机号登录页并点一次「获取验证码」，再重新检测"
    return "在 QQ 里完成一次短信验证后重新检测"


def detect_login_path(adb: str) -> PathDetectResult:
    version = get_qq_version(adb)
    logcat = _read_qq_logcat(adb)
    return detect_from_logcat_text(logcat, version)


def main(argv: list[str] | None = None) -> int:
    from qq_bind_client.adb_helper import find_adb, list_devices

    p = argparse.ArgumentParser(description="检测 QQ 短信查绑走 wtlogin 还是 NTLogin")
    p.add_argument("--adb", default="", help="adb 路径")
    args = p.parse_args(argv)

    adb = find_adb(args.adb)
    if not adb:
        print("错误: 找不到 adb", file=sys.stderr)
        return 2
    if not list_devices(adb):
        print("错误: 无已连接设备", file=sys.stderr)
        return 2

    result = detect_login_path(adb)
    for line in result.lines():
        print(line)
    return 0 if result.path != "unknown" else 1


if __name__ == "__main__":
    raise SystemExit(main())
