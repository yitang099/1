#!/usr/bin/env python3
"""
8081 直连查号测验客户端 — 仅走 SMS 通道，不依赖 9110 计费。

用法:
  python3 -m sms8081_client
  python3 sms8081_client/run.py
"""
from __future__ import annotations

import argparse
import re
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from sms8081_client.api import FAIL_KEYWORDS, Sms8081Client, clean_result_data
from sms8081_client.config import load_config, save_config


ROW_COUNT = 4


class Sms8081App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("8081 查号测验客户端")
        self.geometry("900x520")
        self.minsize(780, 460)

        self.cfg = load_config()
        self.client = self._make_client()
        self.order_data: list[dict] = [{} for _ in range(ROW_COUNT)]

        self._build_ui()
        self.after(400, self._refresh_balance)

    def _make_client(self) -> Sms8081Client:
        return Sms8081Client(
            sms_base=self.cfg["sms_base"],
            api_secret=self.cfg["api_secret"],
            proxy=self.cfg.get("proxy") or None,
        )

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="SMS地址:").grid(row=0, column=0, sticky=tk.W)
        self.sms_var = tk.StringVar(value=self.cfg.get("sms_base", ""))
        ttk.Entry(top, textvariable=self.sms_var, width=34).grid(row=0, column=1, padx=4)

        ttk.Label(top, text="Secret:").grid(row=0, column=2, sticky=tk.W)
        self.secret_var = tk.StringVar(value=self.cfg.get("api_secret", ""))
        ttk.Entry(top, textvariable=self.secret_var, width=36, show="*").grid(row=0, column=3, padx=4)

        ttk.Button(top, text="保存配置", command=self._save_config).grid(row=0, column=4, padx=4)
        ttk.Button(top, text="查通道余额", command=self._refresh_balance).grid(row=0, column=5, padx=4)
        ttk.Button(top, text="设置", command=self._open_settings).grid(row=0, column=6, padx=4)

        self.balance_var = tk.StringVar(value="通道余额: --")
        ttk.Label(top, textvariable=self.balance_var, font=("", 10, "bold")).grid(
            row=0, column=7, padx=10, sticky=tk.E
        )
        top.columnconfigure(7, weight=1)

        area_row = ttk.Frame(self, padding=(10, 0, 10, 6))
        area_row.pack(fill=tk.X)
        ttk.Label(area_row, text="区号:").pack(side=tk.LEFT)
        self.area_var = tk.StringVar(value=str(self.cfg.get("area_code", "86")))
        ttk.Entry(area_row, textvariable=self.area_var, width=6).pack(side=tk.LEFT, padx=6)
        ttk.Label(
            area_row,
            text="流程: 填 Secret → 填手机号点查询 → 收短信填验证码 → 提交 → 自动轮询结果",
            foreground="#666",
        ).pack(side=tk.LEFT, padx=8)

        table = ttk.Frame(self, padding=10)
        table.pack(fill=tk.BOTH, expand=True)
        for col, text in enumerate(("#", "手机号", "验证码", "操作", "状态 / 结果")):
            ttk.Label(table, text=text, font=("", 10, "bold")).grid(row=0, column=col, sticky=tk.W, pady=(0, 6))

        self.phone_entries: list[ttk.Entry] = []
        self.code_entries: list[ttk.Entry] = []
        self.status_labels: list[ttk.Label] = []

        for i in range(ROW_COUNT):
            r = i + 1
            ttk.Label(table, text=str(i + 1)).grid(row=r, column=0, sticky=tk.W, pady=4)
            pe = ttk.Entry(table, width=16)
            pe.grid(row=r, column=1, padx=4, pady=4, sticky=tk.W)
            self.phone_entries.append(pe)
            ce = ttk.Entry(table, width=12)
            ce.grid(row=r, column=2, padx=4, pady=4, sticky=tk.W)
            self.code_entries.append(ce)
            btns = ttk.Frame(table)
            btns.grid(row=r, column=3, padx=4, pady=4, sticky=tk.W)
            ttk.Button(btns, text="查询", width=6, command=lambda row=i: self._submit_order(row)).pack(
                side=tk.LEFT, padx=2
            )
            ttk.Button(btns, text="提交验证码", width=10, command=lambda row=i: self._submit_code(row)).pack(
                side=tk.LEFT, padx=2
            )
            ttk.Button(btns, text="停止", width=6, command=lambda row=i: self._stop_row(row)).pack(
                side=tk.LEFT, padx=2
            )
            st = ttk.Label(table, text="待命", wraplength=360, justify=tk.LEFT)
            st.grid(row=r, column=4, padx=4, pady=4, sticky=tk.W)
            self.status_labels.append(st)
        table.columnconfigure(4, weight=1)

        bottom = ttk.Frame(self, padding=(10, 0, 10, 10))
        bottom.pack(fill=tk.X)
        self.log_var = tk.StringVar(value="就绪 — 仅测验 8081 通道，消耗通道余额")
        ttk.Label(bottom, textvariable=self.log_var, foreground="#444").pack(anchor=tk.W)

    def _reload_client(self) -> None:
        self.client = self._make_client()

    def _save_config(self) -> None:
        self.cfg["sms_base"] = self.sms_var.get().strip()
        self.cfg["api_secret"] = self.secret_var.get().strip()
        self.cfg["area_code"] = self.area_var.get().strip() or "86"
        save_config(self.cfg)
        self._reload_client()
        self._set_log("配置已保存")
        messagebox.showinfo("提示", "配置已保存到 sms8081_config.json")

    def _open_settings(self) -> None:
        win = tk.Toplevel(self)
        win.title("设置")
        win.geometry("420x180")
        win.transient(self)
        win.grab_set()
        proxy_var = tk.StringVar(value=self.cfg.get("proxy", ""))
        ttk.Label(win, text="HTTP 代理 (可选)").grid(row=0, column=0, padx=10, pady=12, sticky=tk.W)
        ttk.Entry(win, textvariable=proxy_var, width=40).grid(row=0, column=1, padx=10, pady=12)
        show_var = tk.BooleanVar(value=False)

        def toggle_secret() -> None:
            pass

        def save() -> None:
            self.cfg["proxy"] = proxy_var.get().strip()
            save_config(self.cfg)
            self._reload_client()
            win.destroy()
            self._set_log("代理设置已保存")

        ttk.Button(win, text="保存", command=save).grid(row=1, column=0, columnspan=2, pady=16)

    def _set_log(self, msg: str) -> None:
        self.log_var.set(msg)

    def _set_row_status(self, row: int, text: str, color: str = "#333") -> None:
        def _u() -> None:
            self.status_labels[row].configure(text=text, foreground=color)

        self.after(0, _u)

    def _run_bg(self, fn, *, on_ok=None, on_err=None) -> None:
        def worker() -> None:
            try:
                result = fn()
            except Exception as exc:
                if on_err:
                    self.after(0, lambda: on_err(exc))
                else:
                    self.after(0, lambda: messagebox.showerror("错误", str(exc)))
                return
            if on_ok:
                self.after(0, lambda: on_ok(result))

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_balance(self) -> None:
        self.cfg["sms_base"] = self.sms_var.get().strip()
        self.cfg["api_secret"] = self.secret_var.get().strip()
        self._reload_client()

        def work() -> str:
            return self.client.get_balance()

        self._set_log("查询通道余额...")
        self._run_bg(
            work,
            on_ok=lambda bal: (
                self.balance_var.set(f"通道余额: {bal} 元"),
                self._set_log("余额已更新"),
            ),
            on_err=lambda e: (
                self.balance_var.set("通道余额: 查询失败"),
                self._set_log(str(e)),
                messagebox.showerror("余额查询失败", str(e)),
            ),
        )

    def _submit_order(self, row: int) -> None:
        phone = self.phone_entries[row].get().strip()
        if not phone:
            self._set_row_status(row, "手机号为空", "#c0392b")
            return
        area = self.area_var.get().strip() or "86"
        self.cfg["sms_base"] = self.sms_var.get().strip()
        self.cfg["api_secret"] = self.secret_var.get().strip()
        self._reload_client()
        od = self.order_data[row]
        od.update(stop_polling=False, completed=False, waiting_for_code=False, polling=False)

        def work() -> str:
            return self.client.create_order(phone, area=area)

        self._set_row_status(row, "提交订单中...", "#d68910")

        def on_ok(order_id: str) -> None:
            od.update(order_id=order_id, phone=phone)
            self._set_row_status(row, f"订单已创建，等待短信 ({order_id[:8]}...)", "#27ae60")
            self._refresh_balance()
            self._poll_order(row)

        self._run_bg(work, on_ok=on_ok, on_err=lambda e: self._set_row_status(row, str(e), "#c0392b"))

    def _submit_code(self, row: int) -> None:
        code = self.code_entries[row].get().strip()
        phone = self.phone_entries[row].get().strip()
        if not code:
            self._set_row_status(row, "验证码为空", "#c0392b")
            return

        def work() -> str:
            return self.client.submit_sms_code(phone, code)

        self._set_row_status(row, "提交验证码...", "#d68910")

        def on_ok(resp: str) -> None:
            if "成功" in resp:
                self.order_data[row]["waiting_for_code"] = False
                self._set_row_status(row, "验证码已提交，等待结果...", "#27ae60")
            else:
                self._set_row_status(row, resp, "#c0392b")

        self._run_bg(work, on_ok=on_ok, on_err=lambda e: self._set_row_status(row, str(e), "#c0392b"))

    def _stop_row(self, row: int) -> None:
        self.order_data[row]["stop_polling"] = True
        self._set_row_status(row, "已停止", "#666")

    def _query_order_sync(self, row: int) -> None:
        od = self.order_data[row]
        order_id = od.get("order_id") or ""
        if not order_id:
            self._set_row_status(row, "无订单号", "#c0392b")
            return
        try:
            resp = self.client.query_order(order_id)
        except Exception as exc:
            self._set_row_status(row, f"网络错误: {exc}", "#c0392b")
            return

        code = resp.get("code")
        data = str(resp.get("data") or "")
        err = str(resp.get("err") or "")
        cleaned = clean_result_data(data)

        if code == 0:
            self._set_row_status(row, f"成功: {cleaned[:200]}", "#27ae60")
            od["completed"] = True
            return
        if code == 1 and err:
            m = re.search(r"\b(\d{4,6})\b", err)
            if m:
                self.code_entries[row].delete(0, tk.END)
                self.code_entries[row].insert(0, m.group(1))
            if "请输入验证码" in err or "等待" in err:
                od["waiting_for_code"] = True
                self._set_row_status(row, "请输入验证码后点「提交验证码」", "#d68910")
                return
        if any(k in data + err for k in FAIL_KEYWORDS):
            self._set_row_status(row, f"失败: {err or data}", "#c0392b")
            od["completed"] = True
            return
        self._set_row_status(row, err or "处理中...", "#d68910")

    def _poll_order(self, row: int) -> None:
        def poll_worker() -> None:
            od = self.order_data[row]
            od["polling"] = True
            for _ in range(120):
                if od.get("stop_polling") or od.get("completed"):
                    break
                if od.get("waiting_for_code"):
                    deadline = time.time() + 300
                    while time.time() < deadline:
                        if od.get("stop_polling") or od.get("completed") or not od.get("waiting_for_code"):
                            break
                        time.sleep(1)
                    else:
                        self._set_row_status(row, "等待验证码超时", "#c0392b")
                        break
                self._query_order_sync(row)
                if od.get("completed"):
                    break
                time.sleep(3)
            else:
                if not od.get("completed"):
                    self._set_row_status(row, "查询超时", "#c0392b")
            od["polling"] = False

        threading.Thread(target=poll_worker, daemon=True).start()


def main(argv: list[str] | None = None) -> int:
    try:
        app = Sms8081App()
    except tk.TclError as exc:
        print(f"无法启动 GUI: {exc}", file=sys.stderr)
        print("请使用: python3 -m sms8081_client --cli", file=sys.stderr)
        return 1
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
