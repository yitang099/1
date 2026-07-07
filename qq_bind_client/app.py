#!/usr/bin/env python3
"""QQ 短信查绑 — GUI（Frida 子进程 + 全链路修复）。"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from qq_bind_client.adb_helper import (
    check_frida_version,
    device_abi,
    find_adb,
    find_frida_server,
    frida_check_connection,
    frida_server_running,
    list_devices,
    list_qq_procs_adb,
    push_and_start_frida_server,
    qq_process_running,
    read_phone_prop,
    resolve_frida_server_binary,
    validate_frida_server_file,
    wake_qq_app,
)
from qq_bind_client.config import APP_VERSION, load_config, results_dir, save_config
from qq_bind_client.logcat_runner import LogcatWatcher, dump_and_parse
from qq_bind_client.results import save_result, save_tlv_hex


class QqBindApp(tk.Tk):
    STEPS = (
        "【原理】手机号+短信验证 → QQ内部返回明文QQ → 工具截获",
        "① 启动Frida  ② 一键开始  ③ 到验证码页点「注入并抓取」→ 立刻填验证码提交",
        "④ 没结果 → 点「诊断」  → 登录后点「验证码后抓取」",
    )

    def __init__(self) -> None:
        super().__init__()
        self.title(f"QQ 查绑工具 v{APP_VERSION}")
        self.geometry("740x540")
        self.cfg = load_config()
        self._worker: subprocess.Popen[str] | None = None
        self._worker_queue: queue.Queue[str | None] = queue.Queue()
        self._reader_thread: threading.Thread | None = None
        self._poll_job: str | None = None
        self._logcat: LogcatWatcher | None = None
        self._inject_count = 0
        self._build_ui()
        self._log(f"[*] QQ查绑工具 v{APP_VERSION}")
        self.after(500, self.refresh_devices)

    def _worker_cmd(self, *args: str) -> list[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable, "--frida-worker", *args]
        return [sys.executable, "-m", "qq_bind_client.frida_worker", *args]

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
            ("诊断", self.run_diagnose),
            ("停止", self.stop_all),
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
            ttk.Label(guide, text=line, wraplength=700).pack(anchor=tk.W, pady=1)

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
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def _log_ui(self, msg: str) -> None:
        self.after(0, lambda: self._log(msg))

    def _pick_adb(self) -> None:
        p = filedialog.askopenfilename(title="adb.exe")
        if p:
            self.adb_var.set(p)

    def _pick_frida(self) -> None:
        p = filedialog.askopenfilename(title="frida-server 文件")
        if not p:
            p = filedialog.askdirectory(title="或选解压文件夹")
        if p:
            r = resolve_frida_server_binary(p)
            self.frida_var.set(str(r or p))

    def _save_cfg(self) -> None:
        self.cfg["adb_path"] = self.adb_var.get().strip()
        self.cfg["frida_server_path"] = self.frida_var.get().strip()
        save_config(self.cfg)

    def _adb(self) -> str | None:
        self._save_cfg()
        return find_adb(self.adb_var.get().strip())

    def _open_results(self) -> None:
        os.startfile(str(results_dir()))  # type: ignore[attr-defined]

    def refresh_devices(self) -> None:
        adb = self._adb()
        if not adb:
            self.device_var.set("缺少 adb")
            return
        if not list_devices(adb):
            self.device_var.set("无设备")
            return
        brand = read_phone_prop(adb, "ro.product.brand")
        model = read_phone_prop(adb, "ro.product.model")
        self.device_var.set(
            f"{brand} {model} | {device_abi(adb)} | frida={'开' if frida_server_running(adb) else '关'} | QQ={'开' if qq_process_running(adb) else '关'}"
        )

    def _ensure_frida(self, adb: str) -> str:
        server = find_frida_server(self.frida_var.get().strip())
        if not server:
            raise RuntimeError("请选择 frida-server 文件（不是文件夹）")
        ok, msg = validate_frida_server_file(server)
        if not ok:
            raise RuntimeError(msg)
        vok, vmsg = check_frida_version(server)
        if not vok:
            raise RuntimeError(vmsg)
        if not frida_server_running(adb):
            ok2, m = push_and_start_frida_server(adb, server)
            if not ok2:
                raise RuntimeError(m)
        ok3, m3 = frida_check_connection()
        if not ok3:
            raise RuntimeError(m3)
        return vmsg

    def _run_bg(self, fn, ok=None, err=None) -> None:
        def worker() -> None:
            try:
                r = fn()
            except Exception as e:
                if err:
                    self.after(0, lambda: err(e))
                else:
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
        self._run_bg(
            lambda: self._ensure_frida(adb),
            ok=lambda msg: self._log(f"[OK] Frida 就绪 ({msg})"),
        )

    def _start_logcat(self, adb: str) -> None:
        if self._logcat:
            self._logcat.stop()

        def on_qq(qq: str) -> None:
            self.after(0, lambda: self._on_qq(qq, "logcat"))

        def on_log(msg: str) -> None:
            self._log_ui(f"[logcat] {msg}")

        self._logcat = LogcatWatcher(on_qq, on_log)
        self._logcat.start(adb)

    def one_click_start(self) -> None:
        adb = self._adb()
        if not adb or not list_devices(adb):
            messagebox.showerror("错误", "请连接手机")
            return
        self.stop_all()

        def prep() -> str:
            msg = self._ensure_frida(adb)
            procs = list_qq_procs_adb(adb)
            main = [p for p in procs if ":MSF" not in str(p.get("name", "")).upper()]
            if not main:
                wake_qq_app(adb)
            return msg

        def done(msg: str) -> None:
            self._log(f"[OK] {msg}")
            self._start_logcat(adb)
            self._log("[*] 监听就绪。手机到验证码页 → 点「注入并抓取」→ 立刻填验证码")
            self.status_var.set("等待验证码页…")

        self._run_bg(prep, ok=done)

    def inject_and_capture(self) -> None:
        if self._worker and self._worker.poll() is None:
            messagebox.showinfo("提示", "注入进程已在运行")
            return
        adb = self._adb()
        if not adb:
            return

        def prep() -> str:
            return self._ensure_frida(adb)

        self.status_var.set("启动注入子进程…")
        self._log("[*] 独立进程注入中（界面不卡）…")
        self._inject_count = 0

        def spawn_worker(_: str) -> None:
            cmd = self._worker_cmd("inject", "--adb", adb)
            try:
                worker = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
            except OSError as exc:
                self.after(0, lambda: (
                    self._log(f"[ERR] 无法启动注入进程: {exc}"),
                    messagebox.showerror("错误", str(exc)),
                ))
                return

            def on_started() -> None:
                self._worker = worker
                while True:
                    try:
                        self._worker_queue.get_nowait()
                    except queue.Empty:
                        break
                self._reader_thread = threading.Thread(
                    target=self._read_worker_stdout,
                    args=(worker,),
                    daemon=True,
                )
                self._reader_thread.start()
                self.status_var.set("注入中…")
                self._schedule_poll()

            self.after(0, on_started)

        self._run_bg(prep, ok=spawn_worker)

    def _read_worker_stdout(self, worker: subprocess.Popen[str]) -> None:
        try:
            if worker.stdout:
                for line in worker.stdout:
                    self._worker_queue.put(line)
        except Exception as exc:
            self._worker_queue.put(json.dumps({"type": "error", "text": f"读注入输出: {exc}"}))
        finally:
            self._worker_queue.put(None)

    def _schedule_poll(self) -> None:
        if self._poll_job:
            self.after_cancel(self._poll_job)
        self._poll_job = self.after(100, self._poll_worker)

    def _poll_worker(self) -> None:
        self._poll_job = None
        eof = False
        while True:
            try:
                line = self._worker_queue.get_nowait()
            except queue.Empty:
                break
            if line is None:
                eof = True
                continue
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                self._log(line)
                continue
            self._handle_worker_msg(msg)

        if not self._worker:
            return
        code = self._worker.poll()
        if code is None and not eof:
            self._schedule_poll()
        else:
            if code is not None:
                self._log(f"[*] 注入进程结束 code={code}")
            self._worker = None

    def _handle_worker_msg(self, msg: dict) -> None:
        t = msg.get("type")
        if t == "log":
            self._log(f"[frida] {msg.get('text', '')}")
        elif t == "error":
            self._log(f"[ERR] {msg.get('text', '')}")
            messagebox.showerror("注入错误", str(msg.get("text", "")))
        elif t == "injected":
            self._inject_count += 1
            self.status_var.set(f"已注入 {self._inject_count} 个进程 — 请立刻填验证码")
            self._log(f"[OK] 已注入 {msg.get('name')} pid={msg.get('pid')}")
        elif t == "no_java":
            self._log(f"[WARN] pid={msg.get('pid')} 无 Java")
        elif t == "proc":
            via = f" ({msg.get('via')})" if msg.get("via") else ""
            self._log(f"[诊断] {msg.get('name')} pid={msg.get('pid')}{via}")
        elif t == "ready":
            self.status_var.set("Hook 就绪 — 请立刻填验证码并提交")
        elif t == "qq":
            qq = str(msg.get("qq") or "")
            if qq:
                self._on_qq(qq, str(msg.get("source") or "hook"))
        elif t == "tlv":
            qq = str(msg.get("qq") or "")
            hex_data = str(msg.get("hex") or "")
            key = str(msg.get("key") or "")
            if qq:
                self._on_qq(qq, "tlv")
            elif hex_data:
                path = save_tlv_hex(hex_data, key)
                self._log(f"[tlv] 已保存 hex（待解析）: {path}")
                self._log(f"[tlv] hex 前80: {hex_data[:80]}...")

    def _on_qq(self, qq: str, source: str) -> None:
        path = save_result(qq, source)
        self.qq_var.set(f"QQ号: {qq}")
        self.status_var.set(f"成功: {qq}")
        self._log(f">>> QQ: {qq}  已保存 {path}")

    def run_diagnose(self) -> None:
        adb = self._adb()
        if not adb:
            return
        self._log("[*] 全面诊断中…")

        def spawn() -> None:
            try:
                worker = subprocess.Popen(
                    self._worker_cmd("diagnose", "--adb", adb),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
            except OSError as exc:
                self.after(0, lambda: self._log(f"[ERR] 诊断启动失败: {exc}"))
                return

            def on_started() -> None:
                self._worker = worker
                while True:
                    try:
                        self._worker_queue.get_nowait()
                    except queue.Empty:
                        break
                self._reader_thread = threading.Thread(
                    target=self._read_worker_stdout,
                    args=(worker,),
                    daemon=True,
                )
                self._reader_thread.start()
                self._schedule_poll()

            self.after(0, on_started)

        spawn()
        self.refresh_devices()

    def capture_after_sms(self) -> None:
        adb = self._adb()
        if not adb:
            return
        self._run_bg(lambda: dump_and_parse(adb), ok=self._on_dump)

    def _on_dump(self, r) -> None:
        qq, path, msg = r
        self._log(msg)
        if path:
            self._log(f"日志: {path}")
        if qq:
            self._on_qq(qq, "logcat_dump")
        else:
            messagebox.showinfo(
                "未抓到",
                "logcat 里可能没有 key_uin。\n请确认已用 v1.3.0 注入成功后再填验证码，或把 查Q结果 里的文件发我分析。",
            )

    def stop_all(self) -> None:
        if self._poll_job:
            self.after_cancel(self._poll_job)
            self._poll_job = None
        if self._worker and self._worker.poll() is None:
            self._worker.terminate()
            try:
                self._worker.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._worker.kill()
            self._worker = None
        while True:
            try:
                self._worker_queue.get_nowait()
            except queue.Empty:
                break
        if self._logcat:
            self._logcat.stop()
            self._logcat = None
        self.status_var.set("已停止")
        self._log("[*] 已停止")

    def destroy(self) -> None:
        self.stop_all()
        super().destroy()


def main() -> int:
    QqBindApp().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
