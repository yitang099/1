#!/usr/bin/env python3
"""滑块学习复现 — 手动过一次，相同验证自动拖。"""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from slider_solver.config import RECORDS_DIR, TEMPLATES_DIR, load_config, save_config
from slider_solver.recorder import DragRecorder, RecordOutcome
from slider_solver.records import list_records
from slider_solver.replay import ReplayResult, auto_solve_from_library
from slider_solver.screen_match import Region, save_region_image
from slider_solver.watcher import BackgroundWatcher

APP_VERSION = "1.1.0"


class RegionPicker:
    def __init__(self, on_done) -> None:
        self.on_done = on_done
        self.root = tk.Toplevel()
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.25)
        self.root.configure(bg="black")
        self.canvas = tk.Canvas(self.root, cursor="cross", bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.start_x = self.start_y = 0
        self.rect = None
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

    def _press(self, e) -> None:
        self.start_x, self.start_y = e.x, e.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=2)

    def _drag(self, e) -> None:
        self.canvas.coords(self.rect, self.start_x, self.start_y, e.x, e.y)

    def _release(self, e) -> None:
        x1, y1, x2, y2 = self.start_x, self.start_y, e.x, e.y
        left, top = min(x1, x2), min(y1, y2)
        w, h = abs(x2 - x1), abs(y2 - y1)
        self.root.destroy()
        if w < 10 or h < 10:
            self.on_done(None)
        else:
            self.on_done(Region(left, top, w, h))


class SliderLearnApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"滑块学习复现 v{APP_VERSION}")
        self.geometry("700x580")
        self.cfg = load_config()
        self._recorder: DragRecorder | None = None
        self._watcher = BackgroundWatcher(on_log=self._log, on_replay=self._on_replay)
        self._build()
        self._refresh_records()

    def _build(self) -> None:
        guide = ttk.LabelFrame(self, text="流程（你要的模式）", padding=8)
        guide.pack(fill=tk.X, padx=10, pady=6)
        for line in (
            "① 框选验证码区域（盖住整条滑块）",
            "② 点【开始录制】→ 去你的软件里【手动拖一次】滑块",
            "③ 工具自动保存这张图 + 拖动距离",
            "④ 以后相同验证出现 → 按 F8 或开【后台监听】自动过",
        ):
            ttk.Label(guide, text=line).pack(anchor=tk.W)

        row = ttk.Frame(self, padding=8)
        row.pack(fill=tk.X)
        for text, cmd in (
            ("框选区域", self.pick_region),
            ("开始录制 F9", self.start_record),
            ("自动过 F8", self.auto_replay),
            ("后台监听", self.toggle_watch),
            ("刷新列表", self._refresh_records),
            ("打开记录库", self._open_records),
        ):
            ttk.Button(row, text=text, command=cmd).pack(side=tk.LEFT, padx=3)

        opts = ttk.LabelFrame(self, text="参数", padding=8)
        opts.pack(fill=tk.X, padx=10, pady=4)
        self.offset_x = tk.IntVar(value=int(self.cfg.get("offset_x") or 0))
        self.duration = tk.IntVar(value=int(self.cfg.get("drag_duration_ms") or 900))
        self.threshold = tk.DoubleVar(value=float(self.cfg.get("match_threshold") or 0.88))
        self.interval = tk.IntVar(value=int(self.cfg.get("watch_interval_ms") or 600))

        ttk.Label(opts, text="X微调:").grid(row=0, column=0, sticky=tk.W)
        ttk.Spinbox(opts, from_=-40, to=40, textvariable=self.offset_x, width=6).grid(row=0, column=1, padx=4)
        ttk.Label(opts, text="匹配阈值(越高越严):").grid(row=0, column=2, sticky=tk.W, padx=(8, 0))
        ttk.Spinbox(opts, from_=0.75, to=0.99, increment=0.01, textvariable=self.threshold, width=6).grid(
            row=0, column=3, padx=4
        )
        ttk.Label(opts, text="拖动ms:").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Spinbox(opts, from_=300, to=3000, textvariable=self.duration, width=8).grid(
            row=1, column=1, sticky=tk.W, padx=4, pady=4
        )
        ttk.Label(opts, text="监听间隔ms:").grid(row=1, column=2, sticky=tk.W, padx=(8, 0))
        ttk.Spinbox(opts, from_=200, to=3000, textvariable=self.interval, width=8).grid(row=1, column=3, padx=4)
        ttk.Button(opts, text="保存", command=self._save_params).grid(row=1, column=4, padx=8)

        self.status = tk.StringVar(value="请先框选验证码区域")
        ttk.Label(self, textvariable=self.status, foreground="#1a5276").pack(anchor=tk.W, padx=12)

        recf = ttk.LabelFrame(self, text="已保存的验证（相同图会自动匹配）", padding=6)
        recf.pack(fill=tk.X, padx=10, pady=4)
        self.record_list = tk.Listbox(recf, height=4, font=("Consolas", 9))
        self.record_list.pack(fill=tk.X)

        logf = ttk.LabelFrame(self, text="日志", padding=6)
        logf.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self.log = scrolledtext.ScrolledText(logf, height=10, font=("Consolas", 9))
        self.log.pack(fill=tk.BOTH, expand=True)

        self.bind("<F8>", lambda e: self.auto_replay())
        self.bind("<F9>", lambda e: self.start_record())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _log(self, msg: str) -> None:
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def _save_params(self) -> None:
        self.cfg["offset_x"] = int(self.offset_x.get())
        self.cfg["drag_duration_ms"] = int(self.duration.get())
        self.cfg["match_threshold"] = float(self.threshold.get())
        self.cfg["watch_interval_ms"] = int(self.interval.get())
        save_config(self.cfg)
        self._log("[*] 参数已保存")

    def _open_records(self) -> None:
        import os

        RECORDS_DIR.mkdir(exist_ok=True)
        os.startfile(str(RECORDS_DIR))  # type: ignore[attr-defined]

    def _refresh_records(self) -> None:
        self.record_list.delete(0, tk.END)
        for rec in list_records():
            self.record_list.insert(
                tk.END,
                f"{rec.name}  距离={rec.drag_distance}px  id={rec.id}",
            )

    def pick_region(self) -> None:
        def done(region: Region | None) -> None:
            if not region:
                return
            self.cfg["captcha_region"] = region.as_dict()
            save_config(self.cfg)
            TEMPLATES_DIR.mkdir(exist_ok=True)
            path = TEMPLATES_DIR / "captcha_region_preview.png"
            save_region_image(region, path)
            self._log(f"[OK] 验证码区域: {region.as_dict()}")
            self.status.set("区域已保存，可开始录制")

        self.status.set("拖拽框选验证码区域，Esc 取消")
        RegionPicker(lambda r: self.after(100, lambda: done(r)))

    def start_record(self) -> None:
        self._save_params()
        region = Region.from_dict(self.cfg.get("captcha_region"))
        if not region:
            messagebox.showerror("错误", "请先框选验证码区域")
            return
        if self._recorder:
            messagebox.showinfo("提示", "正在录制中")
            return

        self.status.set("录制中：请去软件里手动拖一次滑块")
        self._log("[*] 录制开始 — 在验证区域内按住滑块拖到终点后松开")

        def on_finish(outcome: RecordOutcome) -> None:
            self.after(0, lambda: self._on_record_done(outcome))

        self._recorder = DragRecorder(
            region,
            duration_ms=int(self.duration.get()),
            on_finish=on_finish,
        )
        self._recorder.start()

    def _on_record_done(self, outcome: RecordOutcome) -> None:
        self._recorder = None
        if outcome.ok:
            self._log(f"[OK] {outcome.message}")
            self.status.set("录制成功")
            self._refresh_records()
        else:
            self._log(f"[FAIL] {outcome.message}")
            self.status.set(outcome.message)

    def auto_replay(self) -> None:
        self._save_params()
        self.status.set("匹配中…")
        self._log("[*] 查找相同验证图…")

        def worker() -> ReplayResult:
            return auto_solve_from_library(self.cfg)

        def done(result: ReplayResult) -> None:
            if result.ok:
                self._log(f"[OK] {result.message}")
                self.status.set("自动拖动完成")
            else:
                self._log(f"[FAIL] {result.message}")
                self.status.set(result.message)

        threading.Thread(target=lambda: self.after(0, lambda: done(worker())), daemon=True).start()

    def _on_replay(self, result: ReplayResult) -> None:
        self.after(0, lambda: self._log(f"[后台] {result.message}"))

    def toggle_watch(self) -> None:
        self._save_params()
        if self._watcher.running:
            self._watcher.stop()
            self.status.set("后台监听已关")
            return
        if not self.cfg.get("captcha_region"):
            messagebox.showerror("错误", "请先框选验证码区域")
            return
        self._watcher.start(interval_ms=int(self.interval.get()))
        self.status.set("后台监听中 — 相同验证会自动拖")

    def _on_close(self) -> None:
        self._watcher.stop()
        if self._recorder:
            self._recorder.stop()
        self.destroy()


def main() -> int:
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    SliderLearnApp().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
