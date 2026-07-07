"""Background Frida hook runner."""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

from qq_bind_client.config import APP_DIR, resource_dir
from qq_bind_client import parse_qq_bind_uin as parser_mod

QQ_PKG = "com.tencent.mobileqq"
MSF_PROC = QQ_PKG + ":MSF"

JAVA_PROBE = """
'use strict';
function probe(attempt) {
  if (typeof Java !== 'undefined' && Java.available) {
    send({ type: 'probe', java: true });
    return;
  }
  if (attempt >= 8) {
    send({ type: 'probe', java: false });
    return;
  }
  setTimeout(function () { probe(attempt + 1); }, 500);
}
probe(0);
"""


def hook_js_path() -> Path:
    for base in (resource_dir(), APP_DIR, Path(__file__).resolve().parent):
        p = base / "frida_hook.js"
        if p.is_file():
            return p
    alt = Path(__file__).resolve().parent.parent / "analysis" / "qq_sms_bind" / "frida_hook.js"
    if alt.is_file():
        return alt
    raise FileNotFoundError("frida_hook.js not found")


def _qq_targets(device, process: str = "", try_msf: bool = True) -> list[str]:
    if process:
        return [process]
    targets: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        if name and name not in seen:
            seen.add(name)
            targets.append(name)

    if try_msf:
        add(MSF_PROC)
    add(QQ_PKG)

    try:
        found: list[str] = []
        for proc in device.enumerate_processes():
            name = proc.name or ""
            if "com.tencent.mobileqq" in name:
                found.append(name)
        found.sort(key=lambda n: (0 if ":MSF" in n.upper() else 1, n))
        for name in found:
            add(name)
    except Exception:
        pass
    return targets


class FridaHookRunner:
    def __init__(self, on_event: Callable[[str, dict], None]) -> None:
        self.on_event = on_event
        self._sessions: list = []
        self._scripts: list = []
        self._injected_names: set[str] = set()
        self._watch_stop = threading.Event()
        self._watch_thread: threading.Thread | None = None
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
            stage = payload.get("stage") or ""
            if stage == "hashmap":
                self.on_event("status", {"text": "Hook 已就绪，请在 QQ 完成短信验证"})
                self.on_event("log", {"text": "✓ Java Hook 已安装 (HashMap)"})
            elif stage == "scan":
                self.on_event("log", {"text": "✓ 类扫描完成，等待短信验证..."})
        elif kind == "no_java":
            pid = payload.get("pid")
            self.on_event("log", {"text": f"进程 pid={pid} 无 Java，已跳过"})
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

    def _detach_pid(self, pid) -> None:
        for script, session in zip(list(self._scripts), list(self._sessions)):
            try:
                if session.pid == pid:
                    script.unload()
                    session.detach()
                    self._scripts.remove(script)
                    self._sessions.remove(session)
                    return
            except Exception:
                pass

    def _probe_java(self, device, target: str) -> bool:
        import frida

        result = {"java": False}
        done = threading.Event()

        def on_msg(msg, _data) -> None:
            if msg.get("type") == "send" and (msg.get("payload") or {}).get("type") == "probe":
                result["java"] = bool(msg["payload"].get("java"))
                done.set()

        try:
            session = device.attach(target)
            script = session.create_script(JAVA_PROBE)
            script.on("message", on_msg)
            script.load()
            done.wait(timeout=6)
            try:
                script.unload()
                session.detach()
            except Exception:
                pass
            return result["java"]
        except frida.ProcessNotFoundError:
            self.on_event("log", {"text": f"进程不存在: {target}"})
        except Exception as exc:
            self.on_event("log", {"text": f"探测 {target} 失败: {exc}"})
        return False

    def _inject(self, device, hook_source: str, target: str, *, spawn_mode: bool = False) -> bool:
        import frida

        if target in self._injected_names:
            return False
        prefix = "var __SPAWN_MODE__ = true;\n" if spawn_mode else "var __SPAWN_MODE__ = false;\n"
        source = prefix + hook_source
        try:
            session = device.attach(target)
            script = session.create_script(source)
            script.on("message", self._handle_message)
            script.load()
            self._sessions.append(session)
            self._scripts.append(script)
            self._injected_names.add(target)
            self.on_event("log", {"text": f"已注入: {target} (pid={session.pid})"})
            return True
        except frida.ProcessNotFoundError:
            self.on_event("log", {"text": f"进程不存在: {target}"})
        except Exception as exc:
            self.on_event("log", {"text": f"注入 {target} 失败: {exc}"})
        return False

    def _start_msf_watcher(self, device, hook_source: str) -> None:
        if self._watch_thread and self._watch_thread.is_alive():
            return
        self._watch_stop.clear()

        def watch() -> None:
            self.on_event("log", {"text": "后台监听 :MSF 进程（短信登录多在 MSF）..."})
            for _ in range(90):
                if self._watch_stop.is_set():
                    return
                if MSF_PROC in self._injected_names:
                    return
                try:
                    if self._probe_java(device, MSF_PROC):
                        if self._inject(device, hook_source, MSF_PROC):
                            self.on_event("status", {"text": "已注入 :MSF，请完成短信验证"})
                            return
                except Exception:
                    pass
                time.sleep(2)
            if MSF_PROC not in self._injected_names:
                self.on_event("log", {"text": "提示: :MSF 未出现，若主进程 Hook 已就绪可继续操作"})

        self._watch_thread = threading.Thread(target=watch, daemon=True)
        self._watch_thread.start()

    def _spawn_inject(self, device, hook_source: str) -> None:
        pid = device.spawn([QQ_PKG])
        session = device.attach(pid)
        script = session.create_script("var __SPAWN_MODE__ = true;\n" + hook_source)
        script.on("message", self._handle_message)
        script.load()
        self._sessions.append(session)
        self._scripts.append(script)
        self._injected_names.add(QQ_PKG)
        device.resume(pid)
        self.on_event("log", {"text": f"已冷启动 QQ 并注入 (pid={pid})"})
        self.on_event("status", {"text": "已冷启动 QQ 并注入，等待 Java 加载（最多 2 分钟）..."})
        self._start_msf_watcher(device, hook_source)

    def start(self, *, spawn: bool = False, process: str = "", try_msf: bool = True) -> None:
        import frida

        self._injected_names.clear()
        self._watch_stop.set()
        hook_source = hook_js_path().read_text(encoding="utf-8")
        device = frida.get_usb_device(timeout=8)
        self.on_event("log", {"text": f"设备: {device.name}"})

        if spawn:
            self._spawn_inject(device, hook_source)
            return

        targets = _qq_targets(device, process, try_msf)
        self.on_event("log", {"text": f"发现 QQ 进程候选: {targets}"})

        java_targets: list[str] = []
        for target in targets:
            if self._probe_java(device, target):
                self.on_event("log", {"text": f"✓ {target} 有 Java 环境"})
                java_targets.append(target)
            else:
                self.on_event("log", {"text": f"跳过 {target}（无 Java，多为 native 辅助进程）"})

        injected = 0
        for target in java_targets:
            if self._inject(device, hook_source, target):
                injected += 1

        if injected == 0:
            self.on_event("log", {"text": "未找到带 Java 的 QQ 进程，自动冷启动 QQ (spawn)..."})
            self._spawn_inject(device, hook_source)
            return

        self._start_msf_watcher(device, hook_source)
        self.on_event("status", {"text": f"Hook 已注入 {injected} 个 Java 进程，请完成短信验证"})

    def stop(self) -> None:
        self._watch_stop.set()
        for script in self._scripts:
            try:
                script.unload()
            except Exception:
                pass
        for session in self._sessions:
            try:
                session.detach()
            except Exception:
                pass
        self._scripts.clear()
        self._sessions.clear()
        self._injected_names.clear()
