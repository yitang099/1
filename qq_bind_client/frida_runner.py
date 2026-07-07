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
    try {
      Java.perform(function () {
        send({ type: 'probe', java: true });
      });
    } catch (e) {
      send({ type: 'probe', java: true });
    }
    return;
  }
  if (attempt >= __PROBE_MAX__) {
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


def _list_qq_processes(device) -> list[str]:
    try:
        return sorted(
            {proc.name for proc in device.enumerate_processes() if "com.tencent.mobileqq" in (proc.name or "")}
        )
    except Exception:
        return []


def _is_msf(name: str) -> bool:
    return ":MSF" in name.upper()


def _prefer_direct_inject(name: str) -> bool:
    """QQ 子进程（尤其 :MSF）探测 Java 易误报，存在则直接注入并等待。"""
    if _is_msf(name):
        return True
    if name != QQ_PKG and ":" in name and "mobileqq" in name:
        return True
    return False


class FridaHookRunner:
    def __init__(self, on_event: Callable[[str, dict], None]) -> None:
        self.on_event = on_event
        self._sessions: list = []
        self._scripts: list = []
        self._injected_names: set[str] = set()
        self._pid_targets: dict[int, str] = {}
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
            target = self._pid_targets.get(pid, "")
            self.on_event("log", {"text": f"跳过 {target or pid}（注入后仍无 Java）"})
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
        target = self._pid_targets.pop(pid, None)
        if target:
            self._injected_names.discard(target)
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

    def _probe_java(self, device, target: str, *, probe_max: int = 12) -> bool:
        import frida

        result = {"java": False}
        done = threading.Event()
        probe_src = f"var __PROBE_MAX__ = {probe_max};\n" + JAVA_PROBE

        def on_msg(msg, _data) -> None:
            if msg.get("type") == "send" and (msg.get("payload") or {}).get("type") == "probe":
                result["java"] = bool(msg["payload"].get("java"))
                done.set()

        try:
            session = device.attach(target)
            script = session.create_script(probe_src)
            script.on("message", on_msg)
            script.load()
            done.wait(timeout=probe_max * 0.5 + 4)
            try:
                script.unload()
                session.detach()
            except Exception:
                pass
            return result["java"]
        except frida.ProcessNotFoundError:
            return False
        except Exception as exc:
            self.on_event("log", {"text": f"探测 {target} 失败: {exc}"})
        return False

    def _inject(self, device, hook_source: str, target: str, *, java_wait: int = 8) -> bool:
        import frida

        if target in self._injected_names:
            return False
        prefix = f"var __JAVA_WAIT_SEC__ = {java_wait};\n"
        source = prefix + hook_source
        try:
            session = device.attach(target)
            script = session.create_script(source)
            script.on("message", self._handle_message)
            script.load()
            self._sessions.append(session)
            self._scripts.append(script)
            self._injected_names.add(target)
            self._pid_targets[session.pid] = target
            self.on_event("log", {"text": f"已注入: {target} (pid={session.pid}, 等待Java最多{java_wait}s)"})
            return True
        except frida.ProcessNotFoundError:
            self.on_event("log", {"text": f"进程不存在: {target}"})
        except Exception as exc:
            self.on_event("log", {"text": f"注入 {target} 失败: {exc}"})
        return False

    def _try_inject_targets(
        self,
        device,
        hook_source: str,
        targets: list[str],
        running: list[str],
        *,
        java_wait_msf: int = 120,
        java_wait_other: int = 60,
    ) -> int:
        injected = 0
        running_set = set(running)
        for target in targets:
            if target in self._injected_names:
                continue
            if target not in running_set:
                continue
            if _prefer_direct_inject(target):
                self.on_event("log", {"text": f"→ {target} 已运行，直接注入（不依赖 Java 探测）"})
                wait = java_wait_msf if _is_msf(target) else java_wait_other
                if self._inject(device, hook_source, target, java_wait=wait):
                    injected += 1
                continue
            if self._probe_java(device, target):
                self.on_event("log", {"text": f"✓ {target} 探测到 Java"})
                if self._inject(device, hook_source, target, java_wait=java_wait_other):
                    injected += 1
            else:
                self.on_event("log", {"text": f"跳过 {target}（主进程多为 native）"})
        return injected

    def _start_java_watcher(self, device, hook_source: str, *, cold_start: bool = False) -> None:
        if self._watch_thread and self._watch_thread.is_alive():
            return
        self._watch_stop.clear()

        def watch() -> None:
            timeout = 180 if cold_start else 90
            self.on_event("log", {"text": "扫描 QQ 子进程，优先直接注入 :MSF..."})
            deadline = time.time() + timeout
            last_list_log = 0.0
            while time.time() < deadline:
                if self._watch_stop.is_set():
                    return
                if MSF_PROC in self._injected_names:
                    hooked = any(
                        self._pid_targets.get(s.pid) == MSF_PROC and s.pid in self._pid_targets
                        for s in self._sessions
                    )
                    if hooked:
                        return

                now = time.time()
                if now - last_list_log >= 15:
                    names = _list_qq_processes(device)
                    if names:
                        self.on_event("log", {"text": f"当前 QQ 进程: {names}"})
                    last_list_log = now

                running = _list_qq_processes(device)
                n = self._try_inject_targets(
                    device,
                    hook_source,
                    _qq_targets(device),
                    running,
                    java_wait_msf=120,
                    java_wait_other=60,
                )
                if n and MSF_PROC in self._injected_names:
                    self.on_event("status", {"text": "已注入 :MSF，等待 Java 加载..."})
                    return
                time.sleep(2)

            names = _list_qq_processes(device)
            self.on_event("log", {"text": f"超时。当前 QQ 进程: {names or '(无)'}"})
            self.on_event(
                "log",
                {"text": "ERROR: :MSF 注入后仍无 Java。请确认 frida/frida-server 均为 17.15.3"},
            )

        self._watch_thread = threading.Thread(target=watch, daemon=True)
        self._watch_thread.start()

    def _spawn_inject(self, device, hook_source: str) -> None:
        pid = device.spawn([QQ_PKG])
        device.resume(pid)
        self.on_event("log", {"text": f"已冷启动 QQ (pid={pid})，等待 :MSF 子进程..."})
        self.on_event("status", {"text": "冷启动中，等待 :MSF 并注入（最多 3 分钟）..."})
        self._start_java_watcher(device, hook_source, cold_start=True)

    def start(self, *, spawn: bool = False, process: str = "", try_msf: bool = True) -> None:
        import frida

        self._injected_names.clear()
        self._pid_targets.clear()
        self._watch_stop.set()
        hook_source = hook_js_path().read_text(encoding="utf-8")
        device = frida.get_usb_device(timeout=8)
        self.on_event("log", {"text": f"设备: {device.name}"})

        if spawn:
            self._spawn_inject(device, hook_source)
            return

        targets = _qq_targets(device, process, try_msf)
        running = _list_qq_processes(device)
        self.on_event("log", {"text": f"发现 QQ 进程候选: {targets}"})
        self.on_event("log", {"text": f"当前运行中: {running or '(无)'}"})

        injected = self._try_inject_targets(device, hook_source, targets, running)

        if injected == 0:
            if MSF_PROC in running or QQ_PKG in running:
                self.on_event("log", {"text": "进程在运行但注入失败，请点停止后重试"})
            else:
                self.on_event("log", {"text": "QQ 未运行，自动冷启动..."})
                self._spawn_inject(device, hook_source)
            return

        if MSF_PROC not in self._injected_names:
            self._start_java_watcher(device, hook_source, cold_start=False)
        self.on_event("status", {"text": f"已注入 {injected} 个进程，等待 Java / 请完成短信验证"})

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
        self._pid_targets.clear()
