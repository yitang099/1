#!/usr/bin/env python3
"""QQ 短信查绑 Hook 客户端 — Windows GUI，连接 Root 手机自动注入。"""
from __future__ import annotations

import os
import subprocess
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
)
from qq_bind_client.config import APP_DIR, load_config, results_dir, save_config
from qq_bind_client.frida_runner import FridaHookRunner
from qq_bind_client.results import save_result


class QqBindApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("QQ 查绑 Hook 工具")
        self.geometry("780x560")
        self.minsize(680, 480)

        self.cfg = load_config()
        self.adb: str | None = None
        self.device_serial = ""
        self.hook_runner: FridaHookRunner | None = None
        self.hook_thread: threading.Thread | None = None
        self._poll_job: str | None = None

        self._build_ui()
        self.after(500, self.refresh_devices)

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="ADB路径:").grid(row=0, column=0, sticky=tk.W)
        self.adb_var = tk.StringVar(value=self.cfg.get("adb_path", ""))
        ttk.Entry(top, textvariable=self.adb_var, width=48).grid(row=0, column=1, padx=4)
        ttk.Button(top, text="浏览", command=self._pick_adb).grid(row=0, column=2)

        ttk.Label(top, text="frida-server:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.frida_var = tk.StringVar(value=self.cfg.get("frida_server_path", ""))
        ttk.Entry(top, textvariable=self.frida_var, width=48).grid(row=1, column=1, padx=4, pady=4)
        ttk.Button(top, text="浏览", command=self._pick_frida).grid(row=1, column=2, pady=4)

        btn_row = ttk.Frame(top)
        btn_row.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=6)
        ttk.Button(btn_row, text="刷新手机", command=self.refresh_devices).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="启动 Frida", command=self.start_frida_server).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="一键开始 Hook", command=lambda: self._start_hook(spawn=False)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="冷启动Hook", command=lambda: self._start_hook(spawn=True)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="停止", command=self.stop_hook).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="打开结果文件夹", command=self._open_results).pack(side=tk.LEFT, padx=2)

        self.status_var = tk.StringVar(value="请 USB 连接 Root 手机")
        ttk.Label(top, textvariable=self.status_var, font=("", 10, "bold"), foreground="#1a5276").grid(
            row=3, column=0, columnspan=3, sticky=tk.W, pady=4
        )

        dev = ttk.LabelFrame(self, text="已连接设备", padding=8)
        dev.pack(fill=tk.X, padx=10, pady=4)
        self.device_var = tk.StringVar(value="未检测到设备")
        ttk.Label(dev, textvariable=self.device_var).pack(anchor=tk.W)

        guide = ttk.LabelFrame(self, text="手机操作（仍需你本人在手机上完成短信验证）", padding=8)
        guide.pack(fill=tk.X, padx=10, pady=4)
        ttk.Label(
            guide,
            text="推荐：先手动打开QQ等5秒 → 点「一键开始Hook」。若失败再完全退出QQ → 点「冷启动Hook」",
            wraplength=720,
        ).pack(anchor=tk.W)

        res = ttk.LabelFrame(self, text="捕获结果", padding=8)
        res.pack(fill=tk.X, padx=10, pady=4)
        self.qq_var = tk.StringVar(value="QQ号: --")
        ttk.Label(res, textvariable=self.qq_var, font=("", 14, "bold"), foreground="#1a7f37").pack(anchor=tk.W)

        logf = ttk.LabelFrame(self, text="日志", padding=8)
        logf.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self.log = scrolledtext.ScrolledText(logf, height=12, font=("Consolas", 9))
        self.log.pack(fill=tk.BOTH, expand=True)

    def _log(self, msg: str) -> None:
        def _u() -> None:
            self.log.insert(tk.END, msg + "\n")
            self.log.see(tk.END)

        self.after(0, _u)

    def _pick_adb(self) -> None:
        path = filedialog.askopenfilename(title="选择 adb.exe", filetypes=[("adb", "adb.exe"), ("all", "*.*")])
        if path:
            self.adb_var.set(path)

    def _pick_frida(self) -> None:
        path = filedialog.askopenfilename(title="选择 frida-server", filetypes=[("all", "*.*")])
        if path:
            self.frida_var.set(path)

    def _save_cfg(self) -> None:
        self.cfg["adb_path"] = self.adb_var.get().strip()
        self.cfg["frida_server_path"] = self.frida_var.get().strip()
        save_config(self.cfg)

    def _open_results(self) -> None:
        folder = str(results_dir())
        if sys.platform == "win32":
            os.startfile(folder)  # type: ignore[attr-defined]
        else:
            messagebox.showinfo("结果", folder)

    def _get_adb(self) -> str | None:
        self._save_cfg()
        adb = find_adb(self.adb_var.get().strip())
        self.adb = adb
        return adb

    def refresh_devices(self) -> None:
        adb = self._get_adb()
        if not adb:
            self.device_var.set("未找到 adb.exe，请安装 platform-tools 或指定路径")
            self.status_var.set("缺少 ADB")
            return
        devices = list_devices(adb)
        if not devices:
            self.device_var.set("无设备（检查 USB 调试 / 安全设置 / 是否点允许）")
            self.status_var.set("等待手机连接")
            return
        d = devices[0]
        self.device_serial = d["serial"]
        brand = read_phone_prop(adb, "ro.product.brand")
        model = read_phone_prop(adb, "ro.product.model")
        abi = device_abi(adb)
        qq_on = "QQ已开" if qq_process_running(adb) else "QQ未开"
        frida_on = "frida运行中" if frida_server_running(adb) else "frida未运行"
        self.device_var.set(f"{brand} {model} | {abi} | {d['serial']} | {qq_on} | {frida_on}")
        self.status_var.set("设备已连接")

    def _run_bg(self, fn, on_ok=None, on_err=None) -> None:
        def worker() -> None:
            try:
                ret = fn()
            except Exception as exc:
                if on_err:
                    self.after(0, lambda: on_err(exc))
                return
            if on_ok:
                self.after(0, lambda: on_ok(ret))

        threading.Thread(target=worker, daemon=True).start()

    def start_frida_server(self) -> None:
        adb = self._get_adb()
        if not adb:
            messagebox.showerror("错误", "未找到 adb.exe")
            return
        server = find_frida_server(self.frida_var.get().strip())
        if not server:
            messagebox.showerror(
                "错误",
                "未找到 frida-server 文件。\n请把 frida-server-版本-android-arm64 放到 exe 同目录。",
            )
            return

        self.status_var.set("正在推送并启动 frida-server...")
        self._log(f"[*] 使用 frida-server: {server}")

        def work() -> str:
            ok, msg = push_and_start_frida_server(adb, server)
            if not ok:
                raise RuntimeError(msg)
            ok2, ps_out = frida_ps(adb)
            if not ok2:
                raise RuntimeError(f"frida-server 可能未起来: {ps_out}")
            return msg

        self._run_bg(
            work,
            on_ok=lambda m: (self._log(f"[OK] {m}"), self.status_var.set("Frida 就绪"), self.refresh_devices()),
            on_err=lambda e: (self._log(f"[ERR] {e}"), messagebox.showerror("Frida 启动失败", str(e))),
        )

    def _start_hook(self, *, spawn: bool = False) -> None:
        if self.hook_thread and self.hook_thread.is_alive():
            messagebox.showinfo("提示", "Hook 已在运行")
            return
        adb = self._get_adb()
        if not adb:
            messagebox.showerror("错误", "未找到 adb")
            return
        if not list_devices(adb):
            messagebox.showerror("错误", "未检测到手机")
            return

        def pipeline() -> None:
            if not frida_server_running(adb):
                server = find_frida_server(self.frida_var.get().strip())
                if not server:
                    raise RuntimeError("请先放置 frida-server 文件并点「启动 Frida」")
                ok, msg = push_and_start_frida_server(adb, server)
                if not ok:
                    raise RuntimeError(msg)
                self.after(0, lambda: self._log(f"[OK] {msg}"))

            runner = FridaHookRunner(self._on_hook_event)
            self.hook_runner = runner
            if spawn:
                runner.start(spawn=True, adb=adb)
            else:
                runner.start(try_msf=bool(self.cfg.get("try_msf_process", True)), adb=adb)

        self.hook_thread = threading.Thread(target=self._wrap_hook(pipeline), daemon=True)
        self.hook_thread.start()

    def start_hook(self) -> None:
        self._start_hook(spawn=False)

    def _wrap_hook(self, fn):
        def inner() -> None:
            try:
                fn()
            except Exception as exc:
                self.after(0, lambda: self._log(f"[ERR] {exc}"))
                self.after(0, lambda: messagebox.showerror("Hook 失败", str(exc)))

        return inner

    def _on_hook_event(self, kind: str, data: dict) -> None:
        if kind == "log":
            self.after(0, lambda: self._log(f"[frida] {data.get('text', '')}"))
        elif kind == "status":
            self.after(0, lambda: self.status_var.set(data.get("text", "")))
        elif kind == "error":
            self.after(0, lambda: self._log(f"[frida-error] {data.get('text', '')}"))
        elif kind == "qq":
            qq = str(data.get("qq") or "")
            src = str(data.get("source") or "")
            if qq:
                path = save_result(qq, src)
                self.after(0, lambda: self.qq_var.set(f"QQ号: {qq}"))
                self.after(0, lambda: self._log(f">>> 捕获 QQ: {qq}  已保存 {path}"))
        elif kind == "tlv":
            qq = data.get("qq") or ""
            if qq:
                path = save_result(str(qq), "tlv543")
                self.after(0, lambda: self.qq_var.set(f"QQ号: {qq}"))
                self.after(0, lambda: self._log(f">>> 从 TLV 解析 QQ: {qq}  已保存 {path}"))
            else:
                hx = (data.get("hex") or "")[:80]
                self.after(0, lambda: self._log(f"[tlv] key={data.get('key')} hex={hx}..."))

    def stop_hook(self) -> None:
        if self.hook_runner:
            try:
                self.hook_runner.stop()
            except Exception:
                pass
            self.hook_runner = None
        self.status_var.set("已停止 Hook")
        self._log("[*] Hook 已停止")

    def destroy(self) -> None:
        self.stop_hook()
        super().destroy()


def main() -> int:
    try:
        app = QqBindApp()
    except tk.TclError as exc:
        print(f"GUI 启动失败: {exc}", file=sys.stderr)
        return 1
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
