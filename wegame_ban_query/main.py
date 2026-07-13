"""WeGame 封号查询 — 读取 data/QQ.ini (WeGameData)，查询封号。"""
from __future__ import annotations

import queue
import threading
import traceback
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from app_paths import ensure_data_dir, get_data_dir, open_data_folder
from query_api import BanRecord, query_ban_history
from wegame_data import SessionInfo, discover_sessions

APP_TITLE = "WeGame 封号查询"
APP_VERSION = "1.5.0"


class BanQueryApp(tk.Tk):
  def __init__(self) -> None:
    super().__init__()
    self.title(f"{APP_TITLE} v{APP_VERSION}")
    self.geometry("920x680")
    self.minsize(760, 520)

    self.data_dir = ensure_data_dir()
    self.qq_uin = tk.StringVar()
    self.status = tk.StringVar(value="把 WeGameData（QQ号.ini）放入 data 文件夹后点重新扫描")
    self.sessions: list[SessionInfo] = []
    self._busy = False
    self._events: queue.Queue = queue.Queue()

    self._build_ui()
    self.after(100, self._poll_events)
    self.after(200, self._scan_sessions)

  def _log(self, msg: str) -> None:
    self.log_box.insert(tk.END, msg + "\n")
    self.log_box.see(tk.END)
    self.status.set(msg)
    self.update_idletasks()

  def _build_ui(self) -> None:
    pad = {"padx": 8, "pady": 6}

    top = ttk.LabelFrame(self, text="数据目录（文件名=QQ号.ini，内容含 0109_0038 / 0107_0001）")
    top.pack(fill=tk.X, **pad)
    path_row = ttk.Frame(top)
    path_row.pack(fill=tk.X, padx=8, pady=8)
    ttk.Label(path_row, text=str(self.data_dir), foreground="#004488").pack(
      side=tk.LEFT, fill=tk.X, expand=True
    )
    ttk.Button(path_row, text="打开 data 文件夹", command=open_data_folder).pack(side=tk.RIGHT, padx=4)
    self.scan_btn = ttk.Button(path_row, text="重新扫描", command=self._scan_sessions)
    self.scan_btn.pack(side=tk.RIGHT)

    qq_frame = ttk.Frame(self)
    qq_frame.pack(fill=tk.X, **pad)
    ttk.Label(qq_frame, text="QQ 号:").pack(side=tk.LEFT)
    entry = ttk.Entry(qq_frame, textvariable=self.qq_uin, width=20)
    entry.pack(side=tk.LEFT, padx=8)
    entry.bind("<Return>", lambda _e: self._start_query())
    self.query_btn = ttk.Button(qq_frame, text="查询封号", command=self._start_query)
    self.query_btn.pack(side=tk.LEFT, padx=4)
    self.refresh_btn = ttk.Button(qq_frame, text="本地QQ刷新CK", command=self._refresh_local)
    self.refresh_btn.pack(side=tk.LEFT)

    mid = ttk.LabelFrame(self, text="data 文件夹内已识别的 QQ")
    mid.pack(fill=tk.X, **pad)
    self.session_list = tk.Listbox(mid, height=4, exportselection=False)
    self.session_list.pack(fill=tk.X, padx=8, pady=6)
    self.session_list.bind("<<ListboxSelect>>", self._on_session_select)
    self.session_list.bind("<Double-Button-1>", lambda _e: self._start_query())

    table_frame = ttk.LabelFrame(self, text="封号记录")
    table_frame.pack(fill=tk.BOTH, expand=True, **pad)
    cols = ("game_name", "reason", "zone", "start_time", "duration")
    self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=10)
    for col, text, width in [
      ("game_name", "游戏", 140),
      ("reason", "原因", 260),
      ("zone", "区服", 120),
      ("start_time", "开始时间", 160),
      ("duration", "时长", 100),
    ]:
      self.tree.heading(col, text=text)
      self.tree.column(col, width=width, anchor=tk.W)
    scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
    self.tree.configure(yscrollcommand=scroll.set)
    self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)
    scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=8)

    log_frame = ttk.LabelFrame(self, text="运行日志（点查询后这里一定会有输出）")
    log_frame.pack(fill=tk.BOTH, **pad)
    self.log_box = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
    self.log_box.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

    bottom = ttk.Frame(self)
    bottom.pack(fill=tk.X, **pad)
    ttk.Label(bottom, textvariable=self.status, foreground="#333").pack(side=tk.LEFT)

  def _poll_events(self) -> None:
    try:
      while True:
        kind, payload = self._events.get_nowait()
        if kind == "log":
          self._log(payload)
        elif kind == "error":
          self._busy = False
          self.query_btn.configure(state=tk.NORMAL)
          self.scan_btn.configure(state=tk.NORMAL)
          if hasattr(self, "refresh_btn"):
            self.refresh_btn.configure(state=tk.NORMAL)
          self._log(f"失败: {payload}")
          messagebox.showerror(APP_TITLE, payload)
        elif kind == "done":
          self._busy = False
          self.query_btn.configure(state=tk.NORMAL)
          self.scan_btn.configure(state=tk.NORMAL)
          if hasattr(self, "refresh_btn"):
            self.refresh_btn.configure(state=tk.NORMAL)
          session, bans, meta = payload
          for item in self.tree.get_children():
            self.tree.delete(item)
          for b in bans:
            self.tree.insert(
              "",
              tk.END,
              values=(b.game_name, b.reason, b.zone, b.start_time, b.duration),
            )
          if bans:
            self._log(f"QQ {session.uin}: 共 {len(bans)} 条封号记录")
          else:
            raw = meta.get("raw_preview")
            hint = ""
            if isinstance(raw, dict):
              hint = str(raw.get("msg") or raw.get("message") or raw.get("ret") or raw)[:200]
            self._log(f"QQ {session.uin}: 无封号记录 {hint}".strip())
    except queue.Empty:
      pass
    self.after(100, self._poll_events)

  def _scan_sessions(self) -> None:
    ensure_data_dir()
    self._log(f"扫描目录: {get_data_dir()}")
    try:
      self.sessions = discover_sessions(get_data_dir())
    except Exception as exc:
      self.sessions = []
      self._log(f"扫描失败: {exc}")
      messagebox.showerror(APP_TITLE, str(exc))
      return

    self.session_list.delete(0, tk.END)
    for s in self.sessions:
      kind = {"wegame_data": "WeGameData", "clientkey": "CK"}.get(s.kind, "Cookie")
      ck = (s.clientkey or "")[:12]
      self.session_list.insert(tk.END, f"QQ {s.uin}  |  {kind}  |  ck={ck}...")

    if not self.sessions:
      self._log("未发现 QQ 数据。请放入形如 3999482145.ini 的 WeGameData 文件")
    else:
      self._log(f"已识别 {len(self.sessions)} 个 QQ")
      if len(self.sessions) == 1:
        self.qq_uin.set(self.sessions[0].uin)

  def _on_session_select(self, _event: tk.Event) -> None:
    idxs = self.session_list.curselection()
    if idxs:
      self.qq_uin.set(self.sessions[idxs[0]].uin)

  def _refresh_local(self) -> None:
    uin = self.qq_uin.get().strip()
    if not uin:
      messagebox.showwarning(APP_TITLE, "请输入 QQ 号")
      return
    self._log(f"尝试从本机已登录 QQ 刷新 {uin} 的 clientkey...")
    self._busy = True
    self.query_btn.configure(state=tk.DISABLED)
    self.scan_btn.configure(state=tk.DISABLED)
    self.refresh_btn.configure(state=tk.DISABLED)

    def work() -> None:
      try:
        from qq_session import fetch_local_clientkey, list_local_uins, session_from_clientkey

        online = list_local_uins()
        self._events.put(("log", f"本机已登录 QQ: {online or '无'}"))
        ck = fetch_local_clientkey(uin)
        if not ck:
          raise ValueError("本机未登录该 QQ，或未开启快捷登录。请用 PC QQ 登录该号后再试")
        cookies = session_from_clientkey(uin, ck)
        # stash into matching session
        for s in self.sessions:
          if s.uin == "".join(ch for ch in uin if ch.isdigit()):
            s.cookies = cookies
            s.clientkey = ck
            break
        self._events.put(("log", f"本地刷新成功，skey={cookies.get('skey','')[:8]}...，可直接点查询封号"))
        self._events.put(("done", (
          type("S", (), {"uin": uin, "cookies": cookies})(),
          [],
          {"raw_preview": {"msg": "CK已刷新，请再点查询封号"}},
        )))
      except Exception as exc:
        self._events.put(("error", str(exc)))

    threading.Thread(target=work, daemon=True).start()

  def _start_query(self) -> None:
    if self._busy:
      self._log("正在查询中，请稍候...")
      return
    uin = self.qq_uin.get().strip()
    if not uin:
      messagebox.showwarning(APP_TITLE, "请输入 QQ 号")
      return

    self._busy = True
    self.query_btn.configure(state=tk.DISABLED)
    self.scan_btn.configure(state=tk.DISABLED)
    if hasattr(self, "refresh_btn"):
      self.refresh_btn.configure(state=tk.DISABLED)
    self._log(f"开始查询 QQ {uin}")
    threading.Thread(target=self._worker, args=(uin,), daemon=True).start()

  def _worker(self, uin: str) -> None:
    try:
      self._events.put(("log", f"解析 data/{uin}.ini ..."))
      session = None
      for s in self.sessions:
        if s.uin == "".join(ch for ch in uin if ch.isdigit()):
          session = s
          break
      if session is None:
        from wegame_data import resolve_session

        session = resolve_session(get_data_dir(), uin)
      else:
        self._events.put(("log", f"使用已扫描会话 kind={session.kind} ck_len={len(session.clientkey)}"))
        session = session.materialize()

      self._events.put(("log", f"已拿到登录态，skey={ (session.cookies.get('skey') or '')[:8] }...，请求 punish_query"))
      bans, meta = query_ban_history(session.uin, session.cookies, timeout=15)
      self._events.put(("done", (session, bans, meta)))
    except Exception as exc:
      detail = traceback.format_exc()
      try:
        (get_data_dir() / "query_error.log").write_text(detail, encoding="utf-8")
      except OSError:
        pass
      self._events.put(("error", str(exc) or detail[-300:]))


def main() -> None:
  import sys

  if len(sys.argv) >= 3 and sys.argv[1] == "--query":
    uin = sys.argv[2]
    ensure_data_dir()
    from wegame_data import resolve_session

    print("data=", get_data_dir())
    session = resolve_session(get_data_dir(), uin)
    print("uin=", session.uin, "skey=", session.cookies.get("skey"))
    bans, meta = query_ban_history(session.uin, session.cookies)
    print("count=", len(bans), "meta=", meta.get("raw_preview"))
    for b in bans:
      print(b)
    return

  app = BanQueryApp()
  app.mainloop()


if __name__ == "__main__":
  main()
