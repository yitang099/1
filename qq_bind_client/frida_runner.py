"""Background Frida hook runner."""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

from qq_bind_client.adb_helper import (
    force_stop_qq,
    list_qq_procs_adb,
    validate_frida_server_file,
    wake_qq_app,
)
from qq_bind_client.config import APP_DIR, resource_dir
from qq_bind_client.logcat_runner import LogcatWatcher
from qq_bind_client import parse_qq_bind_uin as parser_mod

QQ_PKG = "com.tencent.mobileqq"
MSF_PROC = QQ_PKG + ":MSF"


def hook_js_path() -> Path:
    for base in (resource_dir(), APP_DIR, Path(__file__).resolve().parent):
        p = base / "frida_hook.js"
        if p.is_file():
            return p
    alt = Path(__file__).resolve().parent.parent / "analysis" / "qq_sms_bind" / "frida_hook.js"
    if alt.is_file():
        return alt
    raise FileNotFoundError("frida_hook.js not found")


def _is_msf(name: str) -> bool:
    return ":MSF" in name.upper()


def _has_main(procs: list[dict]) -> bool:
    return any(str(p.get("name")) == QQ_PKG for p in procs)


class FridaHookRunner:
    def __init__(self, on_event: Callable[[str, dict], None]) -> None:
        self.on_event = on_event
        self._hooks: list[dict] = []
        self._injected_pids: set[int] = set()
        self._pid_targets: dict[int, str] = {}
        self._watch_stop = threading.Event()
        self._java_ready = threading.Event()
        self._spawn_gating = False
        self._logcat: LogcatWatcher | None = None
        self._parser = parser_mod
        parser_mod.run_self_test()

    def _handle_message(self, message, _data) -> None:
        if message.get("type") == "error":
            self.on_event("error", {"text": message.get("stack") or str(message)})
            return
        if message.get("type") != "send":
            return
        payload = message.get("payload") or {}
        kind = payload.get("type")
        if kind == "log":
            self.on_event("log", {"text": payload.get("msg", "")})
        elif kind == "ready":
            if (payload.get("stage") or "") == "hashmap":
                self._java_ready.set()
                self.on_event("status", {"text": "Hook 已就绪，请在 QQ 完成短信验证"})
                self.on_event("log", {"text": "✓ Java Hook 已安装"})
        elif kind == "no_java":
            pid = payload.get("pid")
            target = self._pid_targets.get(pid, str(pid))
            arts = payload.get("arts") or []
            self.on_event("log", {"text": f"跳过 {target}（无 Java art={','.join(arts) or 'none'}）"})
            self._detach_pid(pid)
        elif kind == "plain_qq":
            self.on_event("qq", {"qq": payload.get("qq"), "source": payload.get("source")})
        elif kind == "tlv543":
            hex_data = (payload.get("hex") or "").replace(" ", "")
            qq = ""
            if hex_data:
                try:
                    result = self._parser.parse_auto(bytes.fromhex(hex_data))
                    if result.accounts:
                        qq = result.accounts[0].key_uin
                except ValueError:
                    pass
            self.on_event("tlv", {"hex": hex_data, "qq": qq, "key": payload.get("key")})

    def _detach_pid(self, pid: int) -> None:
        self._injected_pids.discard(pid)
        self._pid_targets.pop(pid, None)
        for hook in list(self._hooks):
            if hook["pid"] != pid:
                continue
            try:
                hook["script"].unload()
                hook["session"].detach()
            except Exception:
                pass
            self._hooks.remove(hook)
            return

    def _inject_pid(self, device, hook_source: str, pid: int, name: str, *, java_wait: int = 90) -> bool:
        import frida

        if pid in self._injected_pids:
            return False
        source = f"var __JAVA_WAIT_SEC__ = {java_wait};\n" + hook_source
        try:
            session = device.attach(pid)
            script = session.create_script(source)
            script.on("message", self._handle_message)
            script.load()
            self._hooks.append({"session": session, "script": script, "pid": pid, "name": name})
            self._injected_pids.add(pid)
            self._pid_targets[pid] = name
            self.on_event("log", {"text": f"已注入 pid={pid} {name}（等Java {java_wait}s）"})
            return True
        except Exception as exc:
            self.on_event("log", {"text": f"注入 {name} pid={pid} 失败: {exc}"})
        return False

    def _setup_spawn_gating(self, device, hook_source: str) -> None:
        if self._spawn_gating:
            return

        def on_child_added(child) -> None:
            ident = child.identifier or ""
            if "com.tencent.mobileqq" not in ident:
                return
            if child.pid in self._injected_pids:
                return
            self.on_event("log", {"text": f"子进程启动: {ident} pid={child.pid}"})
            wait = 90 if _is_msf(ident) else 120
            self._inject_pid(device, hook_source, child.pid, ident, java_wait=wait)

        device.on("child-added", on_child_added)
        device.enable_spawn_gating()
        self._spawn_gating = True

    def _start_logcat(self, adb: str) -> None:
        if self._logcat:
            self._logcat.stop()

        def on_qq(qq: str) -> None:
            self.on_event("qq", {"qq": qq, "source": "logcat"})

        def on_log(msg: str) -> None:
            self.on_event("log", {"text": msg})

        self._logcat = LogcatWatcher(on_qq, on_log)
        self._logcat.start(adb)

    def _wait_main_and_inject(self, device, hook_source: str, adb: str, *, cold: bool = False) -> None:
        deadline = time.time() + (120 if cold else 90)
        woke = 0
        while time.time() < deadline:
            if self._watch_stop.is_set() or self._java_ready.is_set():
                return
            procs = list_qq_procs_adb(adb)
            names = [f"{p['name']}:{p['pid']}" for p in procs]
            if names:
                self.on_event("log", {"text": f"adb 进程: {names}"})

            has_main = _has_main(procs)
            if not has_main and woke < 2:
                woke += 1
                self.on_event("log", {"text": f"未检测到 QQ 主进程，第{woke}次唤起..."})
                wake_qq_app(adb, force_stop=woke > 1)
                time.sleep(8)
                continue

            if not has_main:
                self.on_event("log", {"text": ">>> 请现在在手机上点击 QQ 图标进入主界面 <<<"})
                time.sleep(5)
                continue

            ordered = sorted(procs, key=lambda p: (1 if _is_msf(str(p["name"])) else 0,))
            for p in ordered:
                pid = int(p["pid"])
                name = str(p["name"])
                if _is_msf(name) and not has_main:
                    continue
                self._inject_pid(device, hook_source, pid, name, java_wait=120 if not _is_msf(name) else 90)
            if self._injected_pids:
                self.on_event("status", {"text": "已注入，等待 Java / logcat 备用监听中"})
                return
            time.sleep(3)

        self.on_event(
            "log",
            {
                "text": "Frida Java Hook 超时。logcat 仍在监听 — 请完成短信验证，若 QQ 号出现即成功"
            },
        )

    def start(
        self,
        *,
        spawn: bool = False,
        process: str = "",
        try_msf: bool = True,
        adb: str | None = None,
        server_path: Path | None = None,
    ) -> None:
        import frida

        if not adb:
            raise RuntimeError("缺少 adb")

        if server_path:
            ok, msg = validate_frida_server_file(server_path)
            self.on_event("log", {"text": msg})
            if not ok:
                raise RuntimeError(msg)

        self._hooks.clear()
        self._injected_pids.clear()
        self._pid_targets.clear()
        self._java_ready.clear()
        self._watch_stop.clear()

        hook_source = hook_js_path().read_text(encoding="utf-8")
        device = frida.get_usb_device(timeout=8)
        self.on_event("log", {"text": f"设备: {device.name}"})
        self.on_event("log", {"text": f"frida-python {frida.__version__}"})
        self._start_logcat(adb)
        self._setup_spawn_gating(device, hook_source)

        if spawn:
            self.on_event("log", {"text": "智能模式: 强制重启 QQ + 监听子进程"})
            force_stop_qq(adb)
            time.sleep(1)
            pid = device.spawn([QQ_PKG])
            device.resume(pid)
            self.on_event("log", {"text": f"已冷启动 QQ pid={pid}"})
            self.on_event("status", {"text": "冷启动中，等待主进程/Java..."})
            self._wait_main_and_inject(device, hook_source, adb, cold=True)
            return

        if process:
            pid = None
            for p in list_qq_procs_adb(adb):
                if p["name"] == process:
                    pid = int(p["pid"])
                    break
            if pid:
                self._inject_pid(device, hook_source, pid, process, java_wait=120)
            return

        procs = list_qq_procs_adb(adb)
        if not _has_main(procs):
            self.on_event("log", {"text": "智能模式: 先唤起 QQ 主界面再注入"})
            wake_qq_app(adb)
            time.sleep(5)

        self.on_event("status", {"text": "智能 Hook 运行中..."})
        self._wait_main_and_inject(device, hook_source, adb, cold=False)

    def stop(self) -> None:
        self._watch_stop.set()
        if self._logcat:
            self._logcat.stop()
            self._logcat = None
        for hook in self._hooks:
            try:
                hook["script"].unload()
            except Exception:
                pass
            try:
                hook["session"].detach()
            except Exception:
                pass
        self._hooks.clear()
        self._injected_pids.clear()
        self._pid_targets.clear()
