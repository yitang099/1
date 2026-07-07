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


class FridaHookRunner:
    def __init__(self, on_event: Callable[[str, dict], None]) -> None:
        self.on_event = on_event
        self._session = None
        self._script = None
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

    def start(self, *, spawn: bool = False, process: str = "", try_msf: bool = True) -> None:
        import frida

        hook_source = hook_js_path().read_text(encoding="utf-8")
        device = frida.get_usb_device(timeout=8)
        self.on_event("log", {"text": f"设备: {device.name}"})

        if spawn:
            pid = device.spawn([QQ_PKG])
            self._session = device.attach(pid)
            self._script = self._session.create_script(hook_source)
            self._script.on("message", self._handle_message)
            self._script.load()
            device.resume(pid)
            self.on_event("status", {"text": "已冷启动并注入 QQ"})
            return

        targets: list[str] = []
        if process:
            targets = [process]
        else:
            targets = [QQ_PKG]
            if try_msf:
                targets.append(QQ_PKG + ":MSF")

        last_err = None
        for target in targets:
            try:
                self._session = device.attach(target)
                self.on_event("status", {"text": f"已附加: {target}"})
                break
            except frida.ProcessNotFoundError as exc:
                last_err = exc
        else:
            raise RuntimeError(f"未找到 QQ 进程，尝试过 {targets}。请先打开 QQ。") from last_err

        self._script = self._session.create_script(hook_source)
        self._script.on("message", self._handle_message)
        self._script.load()
        self.on_event("status", {"text": "Hook 运行中，请在手机完成短信验证"})

    def stop(self) -> None:
        try:
            if self._script:
                self._script.unload()
        except Exception:
            pass
        try:
            if self._session:
                self._session.detach()
        except Exception:
            pass
        self._script = None
        self._session = None
