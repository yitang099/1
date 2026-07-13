"""WeGame 封号查询 — 自带 data 文件夹，放入 WeGame 数据后输入 QQ 查询封号。"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from app_paths import ensure_data_dir, get_data_dir, open_data_folder
from query_api import BanRecord, query_ban_history
from wegame_data import SessionInfo, discover_sessions, resolve_session

APP_TITLE = "WeGame 封号查询"
APP_VERSION = "1.2.0"


class BanQueryApp(tk.Tk):
  def __init__(self) -> None:
    super().__init__()
    self.title(f"{APP_TITLE} v{APP_VERSION}")
    self.geometry("900x600")
    self.minsize(720, 460)

    self.data_dir = ensure_data_dir()
    self.qq_uin = tk.StringVar()
    self.status = tk.StringVar(value="请将 QQ 号对应的 data/CK 文件放入 data 文件夹")
    self.sessions: list[SessionInfo] = []
    self._query_busy = False

    self._build_ui()
    self.after(200, self._scan_sessions)

  def _build_ui(self) -> None:
    pad = {"padx": 8, "pady": 6}

    top = ttk.LabelFrame(self, text="数据目录（把 QQ 号文件放进 data 文件夹，文件名=QQ号）")
    top.pack(fill=tk.X, **pad)

    path_row = ttk.Frame(top)
    path_row.pack(fill=tk.X, padx=8, pady=8)
    ttk.Label(path_row, text=str(self.data_dir), foreground="#004488").pack(side=tk.LEFT, fill=tk.X, expand=True)
    ttk.Button(path_row, text="打开 data 文件夹", command=open_data_folder).pack(side=tk.RIGHT, padx=4)
    self.scan_btn = ttk.Button(path_row, text="重新扫描", command=self._scan_sessions)
    self.scan_btn.pack(side=tk.RIGHT)

    qq_frame = ttk.Frame(self)
    qq_frame.pack(fill=tk.X, **pad)
    ttk.Label(qq_frame, text="QQ 号:").pack(side=tk.LEFT)
    ttk.Entry(qq_frame, textvariable=self.qq_uin, width=20).pack(side=tk.LEFT, padx=8)
    self.query_btn = ttk.Button(qq_frame, text="查询封号", command=self._start_query)
    self.query_btn.pack(side=tk.LEFT)
    self.qq_uin.trace_add("write", lambda *_: self._sync_qq_highlight())

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

  def _set_busy(self, busy: bool) -> None:
    self._query_busy = busy
    state = tk.DISABLED if busy else tk.NORMAL
    self.query_btn.configure(state=state)

  def _scan_sessions(self) -> None:
    ensure_data_dir()
    try:
      self.sessions = discover_sessions(get_data_dir())
    except Exception as exc:
      self.sessions = []
      self.status.set(f"扫描失败: {exc}")
      messagebox.showerror(APP_TITLE, str(exc))
      return

    self.session_list.delete(0, tk.END)
    for s in self.sessions:
      kind = "CK" if s.kind == "clientkey" else "Cookie"
      self.session_list.insert(tk.END, f"QQ {s.uin}  |  {kind}  |  {s.source}")

    if not self.sessions:
      self.status.set("未发现 QQ 数据。把「3999482145」这类 QQ 号文件放进 data 文件夹后点重新扫描")
    else:
      self.status.set(f"已识别 {len(self.sessions)} 个 QQ，选中或输入 QQ 号后查询")
      self._sync_qq_highlight()

  def _sync_qq_highlight(self) -> None:
    target = self.qq_uin.get().strip()
    if not target or not self.sessions:
      return
    for i, s in enumerate(self.sessions):
      if s.uin == target:
        self.session_list.selection_clear(0, tk.END)
        self.session_list.selection_set(i)
        self.session_list.see(i)
        return

  def _on_session_select(self, _event: tk.Event) -> None:
    idxs = self.session_list.curselection()
    if idxs:
      self.qq_uin.set(self.sessions[idxs[0]].uin)

  def _start_query(self) -> None:
    if self._query_busy:
      return
    uin = self.qq_uin.get().strip()
    if not uin:
      messagebox.showwarning(APP_TITLE, "请输入 QQ 号")
      return
    self._set_busy(True)
    self.status.set(f"正在查询 QQ {uin} ...")
    threading.Thread(target=self._run_query, args=(uin,), daemon=True).start()

  def _run_query(self, uin: str) -> None:
    try:
      session = resolve_session(get_data_dir(), uin)
      bans, meta = query_ban_history(session.uin, session.cookies)
    except Exception as exc:
      msg = str(exc)
      self.after(0, lambda m=msg: self._finish_error(m))
      return

    self.after(0, lambda: self._finish_results(session, bans, meta))

  def _finish_error(self, msg: str) -> None:
    self._set_busy(False)
    self.status.set(f"查询失败: {msg}")
    messagebox.showerror(APP_TITLE, msg)

  def _finish_results(self, session: SessionInfo, bans: list[BanRecord], meta: dict) -> None:
    self._set_busy(False)
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
