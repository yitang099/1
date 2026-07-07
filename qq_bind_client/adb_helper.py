"""ADB and frida-server helpers for Windows."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from qq_bind_client.config import APP_DIR, load_config


def _run(cmd: list[str], timeout: float = 30) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except FileNotFoundError:
        return -1, "", f"not found: {cmd[0]}"


def find_adb(explicit: str = "") -> str | None:
    if explicit and Path(explicit).is_file():
        return explicit
    cfg = load_config().get("adb_path") or ""
    if cfg and Path(cfg).is_file():
        return cfg
    found = shutil.which("adb")
    if found:
        return found
    for guess in (
        Path(os.environ.get("LOCALAPPDATA", "")) / "Android/Sdk/platform-tools/adb.exe",
        Path("C:/platform-tools/adb.exe"),
        APP_DIR / "platform-tools/adb.exe",
    ):
        if guess.is_file():
            return str(guess)
    return None


def list_devices(adb: str) -> list[dict[str, str]]:
    code, out, _ = _run([adb, "devices", "-l"])
    if code != 0:
        return []
    devices: list[dict[str, str]] = []
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line or "offline" in line or "unauthorized" in line:
            continue
        parts = line.split()
        if len(parts) < 2 or parts[1] != "device":
            continue
        serial = parts[0]
        model = ""
        for p in parts[2:]:
            if p.startswith("model:"):
                model = p.split(":", 1)[-1]
        devices.append({"serial": serial, "model": model or serial})
    return devices


def device_abi(adb: str) -> str:
    _, out, _ = _run([adb, "shell", "getprop", "ro.product.cpu.abi"])
    abi = out.strip() or "arm64-v8a"
    if "arm64" in abi:
        return "arm64"
    if "armeabi" in abi:
        return "arm"
    if "x86_64" in abi:
        return "x86_64"
    if "x86" in abi:
        return "x86"
    return "arm64"


def find_frida_server(explicit: str = "") -> Path | None:
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
    cfg = load_config().get("frida_server_path") or ""
    if cfg and Path(cfg).is_file():
        return Path(cfg)
    try:
        import frida

        ver = frida.__version__
    except ImportError:
        ver = None
    names: list[str] = []
    if ver:
        for arch in ("arm64", "arm", "x86_64", "x86"):
            names.append(f"frida-server-{ver}-android-{arch}")
    names.extend(["frida-server", "frida-server.exe"])
    for name in names:
        p = APP_DIR / name
        if p.is_file():
            return p
    for p in APP_DIR.glob("frida-server-*-android-*"):
        if p.is_file():
            return p
    return None


def frida_server_running(adb: str) -> bool:
    _, out, _ = _run([adb, "shell", "su", "-c", "ps -A | grep frida-server"])
    return "frida-server" in out


def push_and_start_frida_server(adb: str, server: Path) -> tuple[bool, str]:
    remote = "/data/local/tmp/frida-server"
    code, out, err = _run([adb, "push", str(server), remote], timeout=120)
    if code != 0:
        return False, f"push 失败: {err or out}"
    cmds = [
        f"chmod 755 {remote}",
        f"pkill frida-server 2>/dev/null; {remote} -D &",
    ]
    for c in cmds:
        code, out, err = _run([adb, "shell", "su", "-c", c], timeout=15)
        if code != 0 and "pkill" not in c:
            return False, f"启动失败(需要 Root/Magisk 授权): {err or out}"
    return True, "frida-server 已启动"


def frida_ps(adb: str) -> tuple[bool, str]:
    code, out, err = _run(["frida-ps", "-U"], timeout=15)
    if code != 0:
        return False, err or out or "frida-ps 失败"
    return True, out


def qq_process_running(adb: str, pkg: str = "com.tencent.mobileqq") -> bool:
    _, out, _ = _run([adb, "shell", "pidof", pkg])
    return bool(out.strip())


def read_phone_prop(adb: str, key: str) -> str:
    _, out, _ = _run([adb, "shell", "getprop", key])
    return out.strip()
