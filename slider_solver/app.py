#!/usr/bin/env python3
"""滑块学习复现 — 手动过一次，相同验证自动拖。"""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from slider_solver.config import RECORDS_DIR, TEMPLATES_DIR, load_config, save_config
from slider_solver.dynamic_solver import DynamicResult, solve_dynamic
from slider_solver.recorder import DragRecorder, RecordOutcome
from slider_solver.records import list_records
from slider_solver.replay import ReplayResult, auto_solve_from_library
from slider_solver.screen_match import Region, save_region_image
from slider_solver.watcher import BackgroundWatcher

APP_VERSION = "1.2.0"


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
        self._watcher = BackgroundWatcher(
            on_log=self._log,
            on_replay=self._on_replay,
            on_dynamic=self._on_dynamic,
        )
        self._build()
        self._refresh_records()

    def _build(self) -> None:
        modef = ttk.LabelFrame(self, text="模式", padding=8)
        modef.pack(fill=tk.X, padx=10, pady=4)
        self.mode_var = tk.StringVar(value=self.cfg.get("mode") or "dynamic")
        ttk.Radiobutton(
            modef,
            text="动态（图每次变，自动识别缺口）— 推荐",
            variable=self.mode_var,
            value="dynamic",
            command=self._on_mode_change,
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            modef,
            text="静态（图完全一样，录一次复现）",
            variable=self.mode_var,
            value="static",
            command=self._on_mode_change,
        ).pack(anchor=tk.W)

        guide = ttk.LabelFrame(self, text="动态模式怎么用", padding=8)
        guide.pack(fill=tk.X, padx=10, pady=4)
        for line in (
            "① 框选验证码区域  ② 框选【滑块按钮】  ③ 框选【拼图块】(可选，提高准确率)",
            "④ 弹出滑块后点【预览识别】看红线是否对准缺口  ⑤ F8 自动拖 / 开后台监听",
            "拖不准就调【X微调】；预览图在 output/dynamic_preview.png",
        ):
            ttk.Label(guide, text=line).pack(anchor=tk.W)

        row = ttk.Frame(self, padding=8)
        row.pack(fill=tk.X)
        for text, cmd in (
            ("框选区域", self.pick_region),
            ("滑块按钮", self.pick_knob),
            ("拼图块", self.pick_piece),
            ("预览识别", self.preview_dynamic),
            ("自动过 F8", self.auto_replay),
            ("录制 F9", self.start_record),
            ("后台监听", self.toggle_watch),
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

    def _on_mode_change(self) -> None:
        self.cfg["mode"] = self.mode_var.get()
        save_config(self.cfg)
        self._log(f"[*] 模式: {self.cfg['mode']}")

    def _save_params(self) -> None:
        self.cfg["mode"] = self.mode_var.get()
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

    def pick_knob(self) -> None:
        def done(region: Region | None) -> None:
            if not region:
                return
            TEMPLATES_DIR.mkdir(exist_ok=True)
            path = TEMPLATES_DIR / "knob.png"
            save_region_image(region, path)
            self.cfg["knob_template"] = str(path)
            save_config(self.cfg)
            self._log(f"[OK] 滑块按钮: {path}")

        self._pick_region_short("框选左边可拖动的小方块", done)

    def pick_piece(self) -> None:
        def done(region: Region | None) -> None:
            if not region:
                return
            TEMPLATES_DIR.mkdir(exist_ok=True)
            path = TEMPLATES_DIR / "piece.png"
            save_region_image(region, path)
            self.cfg["piece_template"] = str(path)
            save_config(self.cfg)
            self._log(f"[OK] 拼图块: {path}")

        self._pick_region_short("框选拼图小图(或缺口形状)", done)

    def _pick_region_short(self, title: str, on_save) -> None:
        self.status.set(title)
        RegionPicker(lambda r: self.after(100, lambda: on_save(r)))

    def preview_dynamic(self) -> None:
        self._save_params()
        self._log("[*] 预览动态识别…")

        def worker():
            return solve_dynamic(self.cfg, preview=True)

        def done(r: DynamicResult) -> None:
            self._log(("[OK] " if r.ok else "[FAIL] ") + r.message)
            if r.ok:
                self.status.set("见 output/dynamic_preview.png")

        threading.Thread(target=lambda: self.after(0, lambda: done(worker())), daemon=True).start()

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
        mode = self.mode_var.get()

        if mode == "dynamic":
            self.status.set("动态识别中…")
            self._log("[*] 动态模式：重新识别缺口…")

            def worker_d() -> DynamicResult:
                return solve_dynamic(self.cfg)

            def done_d(r: DynamicResult) -> None:
                if r.ok:
                    self._log(f"[OK] {r.message}")
                    self.status.set("拖动完成")
                else:
                    self._log(f"[FAIL] {r.message}")
                    self.status.set(r.message)

            threading.Thread(target=lambda: self.after(0, lambda: done_d(worker_d())), daemon=True).start()
            return

        self.status.set("静态匹配中…")
        self._log("[*] 静态模式：查找相同验证图…")

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

    def _on_dynamic(self, result: DynamicResult) -> None:
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
        m = self.mode_var.get()
        self.status.set(f"后台监听({m})中")

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
