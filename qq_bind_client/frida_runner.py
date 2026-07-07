"""Background Frida hook runner."""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

from qq_bind_client.config import APP_DIR, resource_dir
from qq_bind_client import parse_qq_bind_uin as parser_mod
from qq_bind_client.adb_helper import wake_qq_app

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


def _target_pid(device, target: str) -> int | None:
    try:
        for proc in device.enumerate_processes():
            if proc.name == target:
                return int(proc.pid)
    except Exception:
        pass
    return None


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
        self._hooks: list[dict] = []
        self._injected_names: set[str] = set()
        self._pid_targets: dict[int, str] = {}
        self._watch_stop = threading.Event()
        self._watch_thread: threading.Thread | None = None
        self._spawn_gating = False
        self._hook_source = ""
        self._device = None
        self._java_ready = threading.Event()
        self._wake_attempts = 0
        self._manual_wake_hinted = False
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
                self._java_ready.set()
                self.on_event("status", {"text": "Hook 已就绪，请在 QQ 完成短信验证"})
                self.on_event("log", {"text": "✓ Java Hook 已安装 (HashMap)"})
            elif stage == "scan":
                self.on_event("log", {"text": "✓ 类扫描完成，等待短信验证..."})
        elif kind == "no_java":
            pid = payload.get("pid")
            target = self._pid_targets.get(pid, "")
            arts = payload.get("arts") or []
            art_txt = f" art=[{','.join(arts)}]" if arts else ""
            self.on_event("log", {"text": f"跳过 {target or pid}（无 Java{art_txt}）"})
            self._detach_pid(pid)
            if target == MSF_PROC and not arts:
                self.on_event(
                    "log",
                    {
                        "text": "提示: :MSF 可能为纯 native 服务。请确保 QQ 主界面已打开（不只是后台 MSF）"
                    },
                )
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
            pid = _target_pid(device, target)
            if pid is None:
                self.on_event("log", {"text": f"进程不存在: {target}"})
                return False
            session = device.attach(pid)
            script = session.create_script(source)
            script.on("message", self._handle_message)
            script.load()
            self._hooks.append({"session": session, "script": script, "pid": pid, "target": target})
            self._injected_names.add(target)
            self._pid_targets[pid] = target
            self.on_event("log", {"text": f"已注入: {target} (pid={pid}, 等待Java最多{java_wait}s)"})
            return True
        except frida.ProcessNotFoundError:
            self.on_event("log", {"text": f"进程不存在: {target}"})
        except Exception as exc:
            self.on_event("log", {"text": f"注入 {target} 失败: {exc}"})
        return False

    def _setup_spawn_gating(self, device, hook_source: str) -> None:
        if self._spawn_gating:
            return
        self._device = device
        self._hook_source = hook_source

        def on_child_added(child) -> None:
            ident = child.identifier or ""
            if "com.tencent.mobileqq" not in ident:
                return
            if ident in self._injected_names:
                return
            self.on_event("log", {"text": f"捕获子进程: {ident} pid={child.pid}"})
            self._inject(device, hook_source, ident, java_wait=90)

        device.on("child-added", on_child_added)
        device.enable_spawn_gating()
        self._spawn_gating = True
        self.on_event("log", {"text": "已开启子进程监听（新 QQ 进程会自动注入）"})

    def _maybe_wake_qq(self, adb: str | None) -> None:
        if not adb or self._wake_attempts >= 2:
            if not self._manual_wake_hinted:
                self._manual_wake_hinted = True
                self.on_event(
                    "log",
                    {"text": ">>> 请在手机上手动点击 QQ 图标，进入登录/消息主界面 <<<"},
                )
            return
        self._wake_attempts += 1
        force = self._wake_attempts > 1
        self.on_event("log", {"text": f"尝试 adb 唤起 QQ 主进程（第 {self._wake_attempts} 次）..."})
        ok, msg = wake_qq_app(adb, force_stop=force)
        self.on_event("log", {"text": msg})
        if ok:
            time.sleep(8)

    def _prepare_qq_processes(self, device, adb: str | None, *, allow_wake: bool = False) -> list[str]:
        running = _list_qq_processes(device)
        has_main = QQ_PKG in running
        if not has_main and allow_wake and adb:
            self._maybe_wake_qq(adb)
            running = _list_qq_processes(device)
        if QQ_PKG not in running and not self._manual_wake_hinted:
            self.on_event(
                "log",
                {"text": "当前仅有 :MSF 后台服务（无 Java），需要 QQ 主界面进程"},
            )
        return running

    def _try_inject_targets(
        self,
        device,
        hook_source: str,
        targets: list[str],
        running: list[str],
        *,
        java_wait_msf: int = 90,
        java_wait_other: int = 90,
    ) -> int:
        injected = 0
        running_set = set(running)
        has_main = QQ_PKG in running_set
        for target in targets:
            if target in self._injected_names:
                continue
            if target not in running_set:
                continue
            if _is_msf(target) and not has_main:
                self.on_event("log", {"text": f"跳过 {target}（无主进程，:MSF 通常无 Java）"})
                continue
            wait = java_wait_msf if _is_msf(target) else java_wait_other
            self.on_event("log", {"text": f"→ 注入 {target}（等待 Java 最多 {wait}s）"})
            if self._inject(device, hook_source, target, java_wait=wait):
                injected += 1
        return injected

    def _start_java_watcher(self, device, hook_source: str, *, cold_start: bool = False, adb: str | None = None) -> None:
        if self._watch_thread and self._watch_thread.is_alive():
            return
        self._watch_stop.clear()

        def watch() -> None:
            timeout = 180 if cold_start else 120
            self.on_event("log", {"text": "等待 QQ 主进程出现并注入（:MSF 单独运行无 Java）..."})
            deadline = time.time() + timeout
            last_list_log = 0.0
            while time.time() < deadline:
                if self._watch_stop.is_set():
                    return
                if self._java_ready.is_set():
                    return

                now = time.time()
                running = _list_qq_processes(device)
                if QQ_PKG not in running and adb and self._wake_attempts < 2:
                    self._maybe_wake_qq(adb)
                    running = _list_qq_processes(device)

                if now - last_list_log >= 15:
                    if running:
                        self.on_event("log", {"text": f"当前 QQ 进程: {running}"})
                    last_list_log = now

                if QQ_PKG in running or cold_start:
                    self._try_inject_targets(
                        device,
                        hook_source,
                        _qq_targets(device),
                        running,
                        java_wait_msf=90,
                        java_wait_other=90,
                    )
                time.sleep(3)

            names = _list_qq_processes(device)
            self.on_event("log", {"text": f"超时。当前 QQ 进程: {names or '(无)'}"})
            self.on_event(
                "log",
                {
                    "text": "ERROR: 所有进程均无 Java。请确认: ①QQ主界面已打开 ②frida与frida-server同版本(17.15.3)"
                },
            )

        self._watch_thread = threading.Thread(target=watch, daemon=True)
        self._watch_thread.start()

    def _spawn_inject(self, device, hook_source: str, adb: str | None = None) -> None:
        self._setup_spawn_gating(device, hook_source)
        pid = device.spawn([QQ_PKG])
        device.resume(pid)
        self.on_event("log", {"text": f"已冷启动 QQ (pid={pid})，等待子进程..."})
        self.on_event("status", {"text": "冷启动中，监听子进程并注入（最多 3 分钟）..."})
        self._start_java_watcher(device, hook_source, cold_start=True, adb=adb)

    def start(
        self,
        *,
        spawn: bool = False,
        process: str = "",
        try_msf: bool = True,
        adb: str | None = None,
    ) -> None:
        import frida

        self._injected_names.clear()
        self._pid_targets.clear()
        self._java_ready.clear()
        self._wake_attempts = 0
        self._manual_wake_hinted = False
        self._watch_stop.set()
        hook_source = hook_js_path().read_text(encoding="utf-8")
        device = frida.get_usb_device(timeout=8)
        self.on_event("log", {"text": f"设备: {device.name}"})
        self.on_event("log", {"text": f"frida-python {frida.__version__}（需与 frida-server 同版本）"})
        self._setup_spawn_gating(device, hook_source)

        if spawn:
            self._spawn_inject(device, hook_source, adb=adb)
            return

        targets = _qq_targets(device, process, try_msf)
        running = self._prepare_qq_processes(device, adb, allow_wake=True)
        self.on_event("log", {"text": f"发现 QQ 进程候选: {targets}"})
        self.on_event("log", {"text": f"当前运行中: {running or '(无)'}"})

        injected = self._try_inject_targets(device, hook_source, targets, running)

        if injected == 0:
            if running:
                self._start_java_watcher(device, hook_source, cold_start=False, adb=adb)
            else:
                self.on_event("log", {"text": "QQ 未运行，自动冷启动..."})
                self._spawn_inject(device, hook_source, adb=adb)
            return

        self._start_java_watcher(device, hook_source, cold_start=False, adb=adb)
        self.on_event("status", {"text": f"已注入 {injected} 个进程，等待 Java / 请完成短信验证"})

    def stop(self) -> None:
        self._watch_stop.set()
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
        self._injected_names.clear()
        self._pid_targets.clear()
