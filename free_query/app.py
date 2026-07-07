#!/usr/bin/env python3
"""
一码快查 免费查询客户端 — 图形界面

用法:
  python3 -m free_query              # 启动 GUI
  python3 -m free_query --cli        # 命令行交互
  python3 free_query/run.py          # 同上
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from free_query.api import FAIL_KEYWORDS, QueryClient, UserInfo, clean_result_data
from free_query.config import load_config, save_config


ROW_COUNT = 4


class FreeQueryApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("免费查号客户端")
        self.geometry("920x520")
        self.minsize(800, 460)

        self.cfg = load_config()
        self.client = QueryClient(
            main_base=self.cfg["main_base"],
            sms_base=self.cfg["sms_base"],
            proxy=self.cfg.get("proxy") or None,
        )
        self.current_user = self.cfg.get("username") or ""
        self.current_password = self.cfg.get("password") or ""
        self.order_data: list[dict] = [{} for _ in range(ROW_COUNT)]

        self._build_ui()
        self.after(300, self._startup)

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="账号:").grid(row=0, column=0, sticky=tk.W)
        self.user_var = tk.StringVar(value=self.current_user)
        ttk.Entry(top, textvariable=self.user_var, width=18).grid(row=0, column=1, padx=4)

        ttk.Label(top, text="密码:").grid(row=0, column=2, sticky=tk.W)
        self.pass_var = tk.StringVar(value=self.current_password)
        ttk.Entry(top, textvariable=self.pass_var, width=16, show="*").grid(row=0, column=3, padx=4)

        ttk.Button(top, text="登录/注册", command=self._on_login).grid(row=0, column=4, padx=6)
        ttk.Button(top, text="免费充值", command=self._on_topup).grid(row=0, column=5, padx=4)
        ttk.Button(top, text="设置", command=self._on_settings).grid(row=0, column=6, padx=4)

        self.balance_var = tk.StringVar(value="余额: --")
        ttk.Label(top, textvariable=self.balance_var, font=("", 11, "bold")).grid(
            row=0, column=7, padx=12, sticky=tk.E
        )
        top.columnconfigure(7, weight=1)

        area_row = ttk.Frame(self, padding=(10, 0, 10, 6))
        area_row.pack(fill=tk.X)
        ttk.Label(area_row, text="区号:").pack(side=tk.LEFT)
        self.area_var = tk.StringVar(value=str(self.cfg.get("area_code", "86")))
        ttk.Entry(area_row, textvariable=self.area_var, width=6).pack(side=tk.LEFT, padx=6)
        ttk.Label(area_row, text="提示: 先登录 → 自动/手动充值 → 填手机号点查询 → 收短信填验证码点提交", foreground="#666").pack(
            side=tk.LEFT, padx=8
        )

        table = ttk.Frame(self, padding=10)
        table.pack(fill=tk.BOTH, expand=True)

        headers = ("#", "手机号", "短信验证码", "操作", "状态 / 结果")
        for col, text in enumerate(headers):
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

            btn_frame = ttk.Frame(table)
            btn_frame.grid(row=r, column=3, padx=4, pady=4, sticky=tk.W)
            ttk.Button(btn_frame, text="查询", width=6, command=lambda row=i: self._submit_order(row)).pack(
                side=tk.LEFT, padx=2
            )
            ttk.Button(btn_frame, text="提交验证码", width=10, command=lambda row=i: self._submit_code(row)).pack(
                side=tk.LEFT, padx=2
            )
            ttk.Button(btn_frame, text="停止", width=6, command=lambda row=i: self._stop_row(row)).pack(
                side=tk.LEFT, padx=2
            )

            st = ttk.Label(table, text="待命", wraplength=360, justify=tk.LEFT)
            st.grid(row=r, column=4, padx=4, pady=4, sticky=tk.W)
            self.status_labels.append(st)

        table.columnconfigure(4, weight=1)

        bottom = ttk.Frame(self, padding=(10, 0, 10, 10))
        bottom.pack(fill=tk.X)
        self.log_var = tk.StringVar(value="就绪")
        ttk.Label(bottom, textvariable=self.log_var, foreground="#444").pack(anchor=tk.W)

    def _set_log(self, msg: str) -> None:
        self.log_var.set(msg)

    def _set_row_status(self, row: int, text: str, color: str = "#333") -> None:
        def _update() -> None:
            self.status_labels[row].configure(text=text, foreground=color)

        self.after(0, _update)

    def _startup(self) -> None:
        if self.current_user and self.current_password:
            self._run_bg(self._login_worker, on_ok=lambda _: self._refresh_balance())

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

    def _save_session(self) -> None:
        self.cfg["username"] = self.current_user
        self.cfg["password"] = self.current_password
        self.cfg["area_code"] = self.area_var.get().strip() or "86"
        save_config(self.cfg)

    def _reload_client(self) -> None:
        self.client = QueryClient(
            main_base=self.cfg["main_base"],
            sms_base=self.cfg["sms_base"],
            proxy=self.cfg.get("proxy") or None,
        )

    def _login_worker(self) -> str:
        user = self.user_var.get().strip()
        password = self.pass_var.get().strip()
        if not user or not password:
            raise RuntimeError("请填写用户名和密码")
        self._reload_client()
        try:
            self.client.login(user, password)
        except RuntimeError:
            self.client.register(user, password)
        self.current_user = user
        self.current_password = password
        self.client.refresh_sms_base()
        if self.cfg.get("auto_topup", True):
            self.client.ensure_balance(
                user,
                min_balance=float(self.cfg.get("min_balance", 10)),
                topup=float(self.cfg.get("topup_amount", 9999)),
            )
        return user

    def _on_login(self) -> None:
        self._set_log("登录中...")
        self._run_bg(
            self._login_worker,
            on_ok=lambda u: (self._save_session(), self._refresh_balance(), self._set_log(f"已登录: {u}")),
            on_err=lambda e: (self._set_log("登录失败"), messagebox.showerror("登录失败", str(e))),
        )

    def _on_topup(self) -> None:
        if not self.current_user:
            messagebox.showwarning("提示", "请先登录")
            return
        amount = float(self.cfg.get("topup_amount", 9999))

        def work() -> float:
            self.client.refund_balance(self.current_user, amount)
            return self.client.user_info(self.current_user).balance

        self._set_log(f"充值 +{amount}...")
        self._run_bg(
            work,
            on_ok=lambda bal: (self.balance_var.set(f"余额: {bal:.2f}"), self._set_log("充值成功")),
            on_err=lambda e: messagebox.showerror("充值失败", str(e)),
        )

    def _refresh_balance(self) -> None:
        if not self.current_user:
            return

        def work() -> UserInfo:
            return self.client.user_info(self.current_user)

        self._run_bg(
            work,
            on_ok=lambda info: self.balance_var.set(
                f"余额: {info.balance:.2f}  单价: {info.deduct_amount:.2f}"
            ),
        )

    def _on_settings(self) -> None:
        win = tk.Toplevel(self)
        win.title("设置")
        win.geometry("480x320")
        win.transient(self)
        win.grab_set()

        fields = {
            "main_base": ("计费地址 (9110)", self.cfg.get("main_base", "")),
            "sms_base": ("SMS 地址 (8081)", self.cfg.get("sms_base", "")),
            "proxy": ("HTTP 代理 (可选)", self.cfg.get("proxy", "")),
            "topup_amount": ("每次充值金额", str(self.cfg.get("topup_amount", 9999))),
            "min_balance": ("低于此余额自动充值", str(self.cfg.get("min_balance", 10))),
        }
        vars_map: dict[str, tk.StringVar] = {}
        for i, (key, (label, val)) in enumerate(fields.items()):
            ttk.Label(win, text=label).grid(row=i, column=0, sticky=tk.W, padx=10, pady=8)
            var = tk.StringVar(value=val)
            vars_map[key] = var
            ttk.Entry(win, textvariable=var, width=42).grid(row=i, column=1, padx=10, pady=8)

        auto_var = tk.BooleanVar(value=bool(self.cfg.get("auto_topup", True)))
        ttk.Checkbutton(win, text="登录后自动免费充值", variable=auto_var).grid(
            row=len(fields), column=0, columnspan=2, sticky=tk.W, padx=10, pady=8
        )

        def save_and_close() -> None:
            for key in ("main_base", "sms_base", "proxy"):
                self.cfg[key] = vars_map[key].get().strip()
            try:
                self.cfg["topup_amount"] = float(vars_map["topup_amount"].get())
                self.cfg["min_balance"] = float(vars_map["min_balance"].get())
            except ValueError:
                messagebox.showerror("错误", "充值金额请填数字")
                return
            self.cfg["auto_topup"] = auto_var.get()
            save_config(self.cfg)
            self._reload_client()
            win.destroy()
            self._set_log("设置已保存")

        ttk.Button(win, text="保存", command=save_and_close).grid(
            row=len(fields) + 1, column=0, columnspan=2, pady=12
        )

    def _submit_order(self, row: int) -> None:
        if not self.current_user:
            messagebox.showwarning("提示", "请先登录")
            return
        phone = self.phone_entries[row].get().strip()
        if not phone:
            self._set_row_status(row, "手机号为空", "#c0392b")
            return
        area = self.area_var.get().strip() or "86"
        od = self.order_data[row]
        od.update(
            stop_polling=False,
            completed=False,
            waiting_for_code=False,
            polling=False,
            balance_deducted=False,
        )

        def work() -> tuple[str, float]:
            info = self.client.user_info(self.current_user)
            if info.balance < info.deduct_amount:
                self.client.ensure_balance(
                    self.current_user,
                    min_balance=info.deduct_amount,
                    topup=float(self.cfg.get("topup_amount", 9999)),
                )
                info = self.client.user_info(self.current_user)
            order_id = self.client.create_order(phone, area=area)
            self.client.decrease_balance(self.current_user, info.deduct_amount)
            return order_id, info.deduct_amount

        self._set_row_status(row, "提交订单中...", "#d68910")

        def on_ok(res: tuple[str, float]) -> None:
            order_id, deduct = res
            od.update(order_id=order_id, phone=phone, balance_deducted=True)
            self._set_row_status(row, f"订单已创建 ({order_id[:8]}...)，等待短信", "#27ae60")
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
                sms_code = m.group(1)
                self.code_entries[row].delete(0, tk.END)
                self.code_entries[row].insert(0, sms_code)
            if "请输入验证码" in err or "等待" in err:
                od["waiting_for_code"] = True
                self._set_row_status(row, "请输入验证码后点「提交验证码」", "#d68910")
                return
            self._set_row_status(row, err, "#d68910")
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
                        if od.get("stop_polling") or od.get("completed"):
                            break
                        if not od.get("waiting_for_code"):
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


def run_cli() -> int:
    cfg = load_config()
    client = QueryClient(
        main_base=cfg["main_base"],
        sms_base=cfg["sms_base"],
        proxy=cfg.get("proxy") or None,
    )

    print("=== 免费查号 CLI ===\n")
    user = input("用户名 (回车自动注册): ").strip()
    password = input("密码 [chain12345]: ").strip() or "chain12345"
    if not user:
        user = f"free_{int(time.time())}"
        client.register(user, password)
        print(f"已注册: {user}")
    else:
        try:
            client.login(user, password)
            print("登录成功")
        except RuntimeError:
            client.register(user, password)
            print("用户不存在，已自动注册")

    client.refresh_sms_base()
    client.ensure_balance(user, topup=float(cfg.get("topup_amount", 9999)))
    info = client.user_info(user)
    print(f"余额: {info.balance}  单价: {info.deduct_amount}")

    phone = input("手机号: ").strip()
    area = input("区号 [86]: ").strip() or "86"
    order_id = client.create_order(phone, area=area)
    print(f"订单: {order_id}")
    client.decrease_balance(user, info.deduct_amount)
    print("已扣费，请等待手机短信...")

    code = input("短信验证码: ").strip()
    print(client.submit_sms_code(phone, code))

    for i in range(60):
        resp = client.query_order(order_id)
        if resp.get("code") == 0:
            print("\n=== 查询结果 ===")
            print(clean_result_data(str(resp.get("data") or "")))
            cfg["username"] = user
            cfg["password"] = password
            save_config(cfg)
            return 0
        err = resp.get("err") or resp.get("data")
        print(f"[{i+1}] {err}")
        time.sleep(3)

    print("查询超时")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="一码快查 免费查询客户端")
    parser.add_argument("--cli", action="store_true", help="命令行模式（无图形界面）")
    args = parser.parse_args(argv)

    if args.cli:
        return run_cli()

    try:
        app = FreeQueryApp()
    except tk.TclError as exc:
        print(f"无法启动图形界面: {exc}", file=sys.stderr)
        print("请使用: python3 -m free_query --cli", file=sys.stderr)
        return 1
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
