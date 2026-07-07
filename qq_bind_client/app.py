#!/usr/bin/env python3
"""QQ 短信查绑 Hook 客户端 — 简化版 GUI。"""
from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from qq_bind_client.adb_helper import (
    device_abi,
    find_adb,
    find_frida_server,
    frida_ps,
    frida_server_running,
    list_devices,
    push_and_start_frida_server,
    qq_process_running,
    read_phone_prop,
    resolve_frida_server_binary,
    validate_frida_server_file,
)
from qq_bind_client.config import load_config, results_dir, save_config
from qq_bind_client.frida_runner import FridaHookRunner
from qq_bind_client.logcat_runner import dump_and_parse
from qq_bind_client.results import save_result


class QqBindApp(tk.Tk):
    STEPS = (
        "【原理】手机号+短信验证 → QQ内部返回明文QQ号 → 工具截获",
        "① 点「启动Frida」  ② 点「一键开始」",
        "③ 手机QQ走到「输入验证码」页 → 点「注入并抓取」→ 填验证码",
        "④ 没结果就登录后点「验证码后抓取」",
    )

    def __init__(self) -> None:
        super().__init__()
        self.title("QQ 查绑工具（简化版）")
        self.geometry("720x520")
        self.minsize(640, 460)
        self.cfg = load_config()
        self.hook_runner: FridaHookRunner | None = None
        self.hook_thread: threading.Thread | None = None
        self._injecting = False
        self._build_ui()
        self.after(500, self.refresh_devices)

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)
        ttk.Label(top, text="ADB:").grid(row=0, column=0, sticky=tk.W)
        self.adb_var = tk.StringVar(value=self.cfg.get("adb_path", ""))
        ttk.Entry(top, textvariable=self.adb_var, width=50).grid(row=0, column=1, padx=4)
        ttk.Button(top, text="浏览", command=self._pick_adb).grid(row=0, column=2)
        ttk.Label(top, text="frida-server:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.frida_var = tk.StringVar(value=self.cfg.get("frida_server_path", ""))
        ttk.Entry(top, textvariable=self.frida_var, width=50).grid(row=1, column=1, padx=4, pady=4)
        ttk.Button(top, text="浏览", command=self._pick_frida).grid(row=1, column=2, pady=4)

        row = ttk.Frame(top)
        row.grid(row=2, column=0, columnspan=3, pady=8)
        for text, cmd in (
            ("启动 Frida", self.start_frida_server),
            ("一键开始", self.one_click_start),
            ("注入并抓取", self.inject_and_capture),
            ("验证码后抓取", self.capture_after_sms),
            ("停止", self.stop_hook),
            ("打开结果", self._open_results),
        ):
            ttk.Button(row, text=text, command=cmd).pack(side=tk.LEFT, padx=3)

        self.status_var = tk.StringVar(value="请连接手机")
        ttk.Label(top, textvariable=self.status_var, font=("", 11, "bold"), foreground="#1a5276").grid(
            row=3, column=0, columnspan=3, sticky=tk.W
        )

        guide = ttk.LabelFrame(self, text="怎么做", padding=8)
        guide.pack(fill=tk.X, padx=10, pady=4)
        for line in self.STEPS:
            ttk.Label(guide, text=line, wraplength=680).pack(anchor=tk.W, pady=1)

        dev = ttk.LabelFrame(self, text="设备", padding=6)
        dev.pack(fill=tk.X, padx=10, pady=4)
        self.device_var = tk.StringVar(value="未连接")
        ttk.Label(dev, textvariable=self.device_var).pack(anchor=tk.W)

        res = ttk.LabelFrame(self, text="结果", padding=8)
        res.pack(fill=tk.X, padx=10, pady=4)
        self.qq_var = tk.StringVar(value="QQ号: --")
        ttk.Label(res, textvariable=self.qq_var, font=("", 16, "bold"), foreground="#1a7f37").pack(anchor=tk.W)

        logf = ttk.LabelFrame(self, text="日志", padding=6)
        logf.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self.log = scrolledtext.ScrolledText(logf, height=10, font=("Consolas", 9))
        self.log.pack(fill=tk.BOTH, expand=True)

    def _log(self, msg: str) -> None:
        self.after(0, lambda: (self.log.insert(tk.END, msg + "\n"), self.log.see(tk.END)))

    def _pick_adb(self) -> None:
        p = filedialog.askopenfilename(title="adb.exe")
        if p:
            self.adb_var.set(p)

    def _pick_frida(self) -> None:
        p = filedialog.askopenfilename(title="frida-server 文件")
        if not p:
            p = filedialog.askdirectory(title="或选解压后的文件夹")
        if p:
            r = resolve_frida_server_binary(p)
            self.frida_var.set(str(r or p))

    def _save_cfg(self) -> None:
        self.cfg["adb_path"] = self.adb_var.get().strip()
        self.cfg["frida_server_path"] = self.frida_var.get().strip()
        save_config(self.cfg)

    def _open_results(self) -> None:
        os.startfile(str(results_dir()))  # type: ignore[attr-defined]

    def _adb(self) -> str | None:
        self._save_cfg()
        return find_adb(self.adb_var.get().strip())

    def refresh_devices(self) -> None:
        adb = self._adb()
        if not adb:
            self.device_var.set("缺少 adb")
            return
        devs = list_devices(adb)
        if not devs:
            self.device_var.set("无设备")
            return
        d = devs[0]
        brand = read_phone_prop(adb, "ro.product.brand")
        model = read_phone_prop(adb, "ro.product.model")
        abi = device_abi(adb)
        self.device_var.set(
            f"{brand} {model} | {abi} | frida={'开' if frida_server_running(adb) else '关'} | QQ={'开' if qq_process_running(adb) else '关'}"
        )

    def _ensure_frida(self, adb: str) -> None:
        server = find_frida_server(self.frida_var.get().strip())
        if not server:
            raise RuntimeError("请选择 frida-server 文件（17.15.3 arm64）")
        ok, msg = validate_frida_server_file(server)
        if not ok:
            raise RuntimeError(msg)
        if not frida_server_running(adb):
            ok2, m = push_and_start_frida_server(adb, server)
            if not ok2:
                raise RuntimeError(m)
            self._log(f"[OK] {m}")
        ok3, _ = frida_ps(adb)
        if not ok3:
            raise RuntimeError("frida-server 未响应，检查版本是否 17.15.3")

    def _run_bg(self, fn, ok=None) -> None:
        def worker() -> None:
            try:
                r = fn()
            except Exception as e:
                self.after(0, lambda: (self._log(f"[ERR] {e}"), messagebox.showerror("错误", str(e))))
                return
            if ok:
                self.after(0, lambda: ok(r))

        threading.Thread(target=worker, daemon=True).start()

    def start_frida_server(self) -> None:
        adb = self._adb()
        if not adb:
            messagebox.showerror("错误", "缺少 adb")
            return
        self._run_bg(lambda: self._ensure_frida(adb), ok=lambda _: (self._log("[OK] Frida 就绪"), self.refresh_devices()))

    def one_click_start(self) -> None:
        adb = self._adb()
        if not adb or not list_devices(adb):
            messagebox.showerror("错误", "请连接手机")
            return
        self.stop_hook()

        def work() -> None:
            self._ensure_frida(adb)
            runner = FridaHookRunner(self._on_event)
            self.hook_runner = runner
            server = find_frida_server(self.frida_var.get().strip())
            runner.start_deferred(adb, server_path=server)

        self.hook_thread = threading.Thread(target=work, daemon=True)
        self.hook_thread.start()
        self.status_var.set("等待你到验证码页…")
        messagebox.showinfo(
            "下一步",
            "手机操作：\n\nQQ → 手机号登录 → 收短信\n→ 停在「输入验证码」页面\n\n然后点「注入并抓取」",
        )

    def inject_and_capture(self) -> None:
        if not self.hook_runner:
            messagebox.showerror("错误", "请先点「一键开始」")
            return
        try:
            self.hook_runner.inject_now()
            self.status_var.set("已注入，请填验证码")
        except Exception as e:
            messagebox.showerror("注入失败", str(e))

    def capture_after_sms(self) -> None:
        adb = self._adb()
        if not adb:
            return
        self._run_bg(
            lambda: dump_and_parse(adb),
            ok=lambda r: self._on_dump(r),
        )

    def _on_dump(self, r) -> None:
        qq, path, msg = r
        self._log(msg)
        if path:
            self._log(f"日志: {path}")
        if qq:
            p = save_result(qq, "logcat")
            self.qq_var.set(f"QQ号: {qq}")
            self._log(f">>> QQ: {qq}  已保存")
        else:
            messagebox.showinfo("未抓到", "请把 查Q结果 里的 logcat 文件发来分析")

    def _on_event(self, kind: str, data: dict) -> None:
        if kind == "log":
            self._log(f"[frida] {data.get('text', '')}")
        elif kind == "status":
            self.status_var.set(data.get("text", ""))
        elif kind == "qq":
            qq = str(data.get("qq") or "")
            if qq:
                p = save_result(qq, data.get("source", "hook"))
                self.qq_var.set(f"QQ号: {qq}")
                self._log(f">>> QQ: {qq}  已保存 {p}")
        elif kind == "tlv":
            qq = str(data.get("qq") or "")
            if qq:
                p = save_result(qq, "tlv")
                self.qq_var.set(f"QQ号: {qq}")
                self._log(f">>> QQ: {qq}  已保存 {p}")

    def stop_hook(self) -> None:
        if self.hook_runner:
            try:
                self.hook_runner.stop()
            except Exception:
                pass
            self.hook_runner = None
        self.status_var.set("已停止")

    def destroy(self) -> None:
        self.stop_hook()
        super().destroy()


def main() -> int:
    QqBindApp().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
