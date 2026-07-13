"""WeGame 封号查询 — 本地读取登录态，调用腾讯官方 punish_query 接口。"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from query_api import BanRecord, query_ban_history
from wegame_data import SessionInfo, discover_sessions, pick_session

APP_TITLE = "WeGame 封号查询"
APP_VERSION = "1.0.0"


class BanQueryApp(tk.Tk):
  def __init__(self) -> None:
    super().__init__()
    self.title(f"{APP_TITLE} v{APP_VERSION}")
    self.geometry("920x620")
    self.minsize(760, 480)

    self.data_dir = tk.StringVar()
    self.qq_uin = tk.StringVar()
    self.status = tk.StringVar(value="请选择 WeGame data 文件夹")
    self.sessions: list[SessionInfo] = []

    self._build_ui()

  def _build_ui(self) -> None:
    pad = {"padx": 8, "pady": 6}

    top = ttk.Frame(self)
    top.pack(fill=tk.X, **pad)

    ttk.Label(top, text="WeGame 数据目录:").grid(row=0, column=0, sticky=tk.W)
    ttk.Entry(top, textvariable=self.data_dir, width=72).grid(row=0, column=1, sticky=tk.EW, padx=6)
    ttk.Button(top, text="浏览...", command=self._pick_dir).grid(row=0, column=2)
    top.columnconfigure(1, weight=1)

    ttk.Label(top, text="QQ 号:").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
    qq_row = ttk.Frame(top)
    qq_row.grid(row=1, column=1, columnspan=2, sticky=tk.EW, pady=(8, 0))
    ttk.Entry(qq_row, textvariable=self.qq_uin, width=24).pack(side=tk.LEFT)
    ttk.Button(qq_row, text="扫描登录态", command=self._scan_sessions).pack(side=tk.LEFT, padx=8)
    ttk.Button(qq_row, text="查询封号", command=self._start_query).pack(side=tk.LEFT)

    mid = ttk.LabelFrame(self, text="已发现的 QQ 登录态")
    mid.pack(fill=tk.X, **pad)
    self.session_list = tk.Listbox(mid, height=4, exportselection=False)
    self.session_list.pack(fill=tk.X, padx=8, pady=6)
    self.session_list.bind("<<ListboxSelect>>", self._on_session_select)

    table_frame = ttk.LabelFrame(self, text="封号记录")
    table_frame.pack(fill=tk.BOTH, expand=True, **pad)

    cols = ("game_name", "reason", "zone", "start_time", "duration")
    self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=14)
    headings = {
      "game_name": ("游戏", 140),
      "reason": ("原因", 260),
      "zone": ("区服", 120),
      "start_time": ("开始时间", 160),
      "duration": ("时长", 100),
    }
    for col, (text, width) in headings.items():
      self.tree.heading(col, text=text)
      self.tree.column(col, width=width, anchor=tk.W)
    scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
    self.tree.configure(yscrollcommand=scroll.set)
    self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)
    scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=8)

    bottom = ttk.Frame(self)
    bottom.pack(fill=tk.X, **pad)
    ttk.Label(bottom, textvariable=self.status, foreground="#333").pack(side=tk.LEFT)
    ttk.Label(
      bottom,
      text="仅本地查询官方接口，不外传 Cookie",
      foreground="#666",
    ).pack(side=tk.RIGHT)

  def _pick_dir(self) -> None:
    path = filedialog.askdirectory(title="选择 WeGame data 文件夹")
    if path:
      self.data_dir.set(path)
      self._scan_sessions()

  def _scan_sessions(self) -> None:
    path = self.data_dir.get().strip()
    if not path:
      messagebox.showwarning(APP_TITLE, "请先选择 WeGame 数据目录")
      return
    try:
      self.sessions = discover_sessions(path)
    except Exception as exc:
      self.sessions = []
      self.status.set(f"扫描失败: {exc}")
      messagebox.showerror(APP_TITLE, str(exc))
      return

    self.session_list.delete(0, tk.END)
    for s in self.sessions:
      sk = (s.cookies.get("skey") or s.cookies.get("p_skey") or "")[:6]
      self.session_list.insert(tk.END, f"QQ {s.uin}  |  skey={sk}...  |  {s.source}")

    if not self.sessions:
      self.status.set("未找到含 skey 的登录态，请放入 cookies.ini 或 cookies.json")
    else:
      self.status.set(f"发现 {len(self.sessions)} 个登录态")
      if len(self.sessions) == 1:
        self.qq_uin.set(self.sessions[0].uin)

  def _on_session_select(self, _event: tk.Event) -> None:
    idxs = self.session_list.curselection()
    if not idxs:
      return
    self.qq_uin.set(self.sessions[idxs[0]].uin)

  def _start_query(self) -> None:
    threading.Thread(target=self._run_query, daemon=True).start()

  def _run_query(self) -> None:
    self.after(0, lambda: self.status.set("查询中..."))
    path = self.data_dir.get().strip()
    uin = self.qq_uin.get().strip()
    if not path:
      self.after(0, lambda: messagebox.showwarning(APP_TITLE, "请先选择数据目录"))
      return
    if not uin:
      self.after(0, lambda: messagebox.showwarning(APP_TITLE, "请输入 QQ 号"))
      return

    try:
      if not self.sessions:
        self.sessions = discover_sessions(path)
      session = pick_session(self.sessions, uin)
      bans, meta = query_ban_history(session.uin, session.cookies)
    except Exception as exc:
      self.after(0, lambda: self._show_error(str(exc)))
      return

    self.after(0, lambda: self._show_results(session, bans, meta))

  def _show_error(self, msg: str) -> None:
    self.status.set(f"查询失败: {msg}")
    messagebox.showerror(APP_TITLE, msg)

  def _show_results(self, session: SessionInfo, bans: list[BanRecord], meta: dict) -> None:
    for item in self.tree.get_children():
      self.tree.delete(item)
    for b in bans:
      self.tree.insert("", tk.END, values=(b.game_name, b.reason, b.zone, b.start_time, b.duration))

    if bans:
      self.status.set(f"QQ {session.uin}: 共 {len(bans)} 条封号记录")
    else:
      raw = meta.get("raw_preview")
      hint = ""
      if isinstance(raw, dict):
        hint = str(raw.get("msg") or raw.get("message") or raw.get("ret") or "")
      self.status.set(f"QQ {session.uin}: 无封号记录 {hint}".strip())


def main() -> None:
  app = BanQueryApp()
  app.mainloop()


if __name__ == "__main__":
  main()
