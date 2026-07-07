"""Background Frida hook runner."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from qq_bind_client.config import APP_DIR, resource_dir
from qq_bind_client import parse_qq_bind_uin as parser_mod

QQ_PKG = "com.tencent.mobileqq"


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
        add(QQ_PKG + ":MSF")
    add(QQ_PKG)

    try:
        found: list[str] = []
        for proc in device.enumerate_processes():
            name = proc.name or ""
            if "com.tencent.mobileqq" in name:
                found.append(name)
        # MSF 优先，其余按名称
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

    def _inject(self, device, hook_source: str, target: str) -> bool:
        import frida

        try:
            session = device.attach(target)
            script = session.create_script(hook_source)
            script.on("message", self._handle_message)
            script.load()
            self._sessions.append(session)
            self._scripts.append(script)
            self.on_event("log", {"text": f"已注入: {target}"})
            return True
        except frida.ProcessNotFoundError:
            self.on_event("log", {"text": f"进程不存在: {target}"})
        except Exception as exc:
            self.on_event("log", {"text": f"注入 {target} 失败: {exc}"})
        return False

    def start(self, *, spawn: bool = False, process: str = "", try_msf: bool = True) -> None:
        import frida

        hook_source = hook_js_path().read_text(encoding="utf-8")
        device = frida.get_usb_device(timeout=8)
        self.on_event("log", {"text": f"设备: {device.name}"})

        if spawn:
            pid = device.spawn([QQ_PKG])
            session = device.attach(pid)
            script = session.create_script(hook_source)
            script.on("message", self._handle_message)
            script.load()
            self._sessions.append(session)
            self._scripts.append(script)
            device.resume(pid)
            self.on_event("status", {"text": "已冷启动 QQ 并注入，等待 Java 加载..."})
            return

        targets = _qq_targets(device, process, try_msf)
        self.on_event("log", {"text": f"发现 QQ 进程候选: {targets}"})

        injected = 0
        for target in targets:
            if self._inject(device, hook_source, target):
                injected += 1

        if injected == 0:
            self.on_event("log", {"text": "附加失败，尝试冷启动 QQ (spawn)..."})
            pid = device.spawn([QQ_PKG])
            session = device.attach(pid)
            script = session.create_script(hook_source)
            script.on("message", self._handle_message)
            script.load()
            self._sessions.append(session)
            self._scripts.append(script)
            device.resume(pid)
            self.on_event("status", {"text": "已 spawn 注入 QQ，等待 Java..."})
            return

        self.on_event("status", {"text": f"Hook 已注入 {injected} 个进程，请完成短信验证"})

    def stop(self) -> None:
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
