"""WeGame 封号查询 — 自带 data 文件夹，放入 WeGame 数据后输入 QQ 查询封号。"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from app_paths import ensure_data_dir, get_data_dir, open_data_folder
from query_api import BanRecord, query_ban_history
from wegame_data import SessionInfo, discover_sessions, pick_session

APP_TITLE = "WeGame 封号查询"
APP_VERSION = "1.1.0"


class BanQueryApp(tk.Tk):
  def __init__(self) -> None:
    super().__init__()
    self.title(f"{APP_TITLE} v{APP_VERSION}")
    self.geometry("900x600")
    self.minsize(720, 460)

    self.data_dir = ensure_data_dir()
    self.qq_uin = tk.StringVar()
    self.status = tk.StringVar(value="请将 WeGame data 放入软件旁的 data 文件夹")
    self.sessions: list[SessionInfo] = []

    self._build_ui()
    self.after(200, self._scan_sessions)

  def _build_ui(self) -> None:
    pad = {"padx": 8, "pady": 6}

    top = ttk.LabelFrame(self, text="数据目录（软件自带，把 WeGame data 放进去）")
    top.pack(fill=tk.X, **pad)

    path_row = ttk.Frame(top)
    path_row.pack(fill=tk.X, padx=8, pady=8)
    ttk.Label(path_row, text=str(self.data_dir), foreground="#004488").pack(side=tk.LEFT, fill=tk.X, expand=True)
    ttk.Button(path_row, text="打开 data 文件夹", command=open_data_folder).pack(side=tk.RIGHT, padx=4)
    ttk.Button(path_row, text="重新扫描", command=self._scan_sessions).pack(side=tk.RIGHT)

    qq_frame = ttk.Frame(self)
    qq_frame.pack(fill=tk.X, **pad)
    ttk.Label(qq_frame, text="QQ 号:").pack(side=tk.LEFT)
    ttk.Entry(qq_frame, textvariable=self.qq_uin, width=20).pack(side=tk.LEFT, padx=8)
    ttk.Button(qq_frame, text="查询封号", command=self._start_query).pack(side=tk.LEFT)

    mid = ttk.LabelFrame(self, text="data 文件夹内已识别的 QQ")
    mid.pack(fill=tk.X, **pad)
    self.session_list = tk.Listbox(mid, height=4, exportselection=False)
    self.session_list.pack(fill=tk.X, padx=8, pady=6)
    self.session_list.bind("<<ListboxSelect>>", self._on_session_select)
    self.session_list.bind("<Double-Button-1>", lambda _e: self._start_query())

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

  def _scan_sessions(self) -> None:
    path = get_data_dir()
    ensure_data_dir()
    try:
      self.sessions = discover_sessions(path)
    except Exception as exc:
      self.sessions = []
      self.status.set(f"扫描失败: {exc}")
      return

    self.session_list.delete(0, tk.END)
    for s in self.sessions:
      sk = (s.cookies.get("skey") or s.cookies.get("p_skey") or "")[:6]
      self.session_list.insert(tk.END, f"QQ {s.uin}  |  skey={sk}...")

    if not self.sessions:
      self.status.set("data 文件夹为空或未找到登录态，请放入 WeGame data 或 cookies.ini")
    else:
      self.status.set(f"已扫描 data 文件夹，发现 {len(self.sessions)} 个 QQ 登录态")
      if len(self.sessions) == 1:
        self.qq_uin.set(self.sessions[0].uin)

  def _on_session_select(self, _event: tk.Event) -> None:
    idxs = self.session_list.curselection()
    if idxs:
      self.qq_uin.set(self.sessions[idxs[0]].uin)

  def _start_query(self) -> None:
    threading.Thread(target=self._run_query, daemon=True).start()

  def _run_query(self) -> None:
    self.after(0, lambda: self.status.set("查询中..."))
    uin = self.qq_uin.get().strip()
    if not uin:
      self.after(0, lambda: messagebox.showwarning(APP_TITLE, "请输入 QQ 号"))
      return

    try:
      if not self.sessions:
        self.sessions = discover_sessions(get_data_dir())
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
