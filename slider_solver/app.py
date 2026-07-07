#!/usr/bin/env python3
"""桌面软件滑块自动拖动 — Windows 本地测试。"""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from slider_solver.config import TEMPLATES_DIR, load_config, save_config
from slider_solver.screen_match import Region, save_region_image
from slider_solver.solver import solve_once

APP_VERSION = "1.0.0"


class RegionPicker:
    """全屏半透明框选区域。"""

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


class SliderAutoApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"滑块自动拖动 v{APP_VERSION}")
        self.geometry("680x520")
        self.cfg = load_config()
        self._build()

    def _build(self) -> None:
        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)

        guide = ttk.LabelFrame(self, text="怎么用（针对你那个软件）", padding=8)
        guide.pack(fill=tk.X, padx=10, pady=4)
        for line in (
            "① 先打开你的软件，把滑块验证弹出来",
            "② 点【框选验证码区域】——拖一个框盖住整条滑块（含背景图）",
            "③ 点【截取滑块按钮】——再框选那个小方块按钮",
            "④ 点【试跑一次】或按 F8",
            "若总差一点：改【固定距离】或【X微调】",
        ):
            ttk.Label(guide, text=line).pack(anchor=tk.W)

        row = ttk.Frame(top)
        row.pack(fill=tk.X, pady=6)
        for text, cmd in (
            ("框选验证码区域", self.pick_captcha_region),
            ("截取滑块按钮", self.pick_slider_template),
            ("截取背景(可选)", self.pick_bg_template),
            ("试跑一次", self.run_solve),
            ("打开模板目录", self._open_templates),
        ):
            ttk.Button(row, text=text, command=cmd).pack(side=tk.LEFT, padx=3)

        opts = ttk.LabelFrame(self, text="参数", padding=8)
        opts.pack(fill=tk.X, padx=10, pady=4)

        self.manual_dist = tk.IntVar(value=int(self.cfg.get("manual_distance") or 0))
        self.offset_x = tk.IntVar(value=int(self.cfg.get("offset_x") or 0))
        self.duration = tk.IntVar(value=int(self.cfg.get("drag_duration_ms") or 900))

        ttk.Label(opts, text="固定距离(px，0=自动识别):").grid(row=0, column=0, sticky=tk.W)
        ttk.Spinbox(opts, from_=0, to=500, textvariable=self.manual_dist, width=8).grid(
            row=0, column=1, sticky=tk.W, padx=4
        )
        ttk.Label(opts, text="X微调:").grid(row=0, column=2, sticky=tk.W, padx=(12, 0))
        ttk.Spinbox(opts, from_=-40, to=40, textvariable=self.offset_x, width=8).grid(
            row=0, column=3, sticky=tk.W, padx=4
        )
        ttk.Label(opts, text="拖动耗时(ms):").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Spinbox(opts, from_=300, to=3000, textvariable=self.duration, width=8).grid(
            row=1, column=1, sticky=tk.W, padx=4, pady=4
        )
        ttk.Button(opts, text="保存参数", command=self._save_params).grid(row=1, column=2, padx=8)

        self.status = tk.StringVar(value="请先框选验证码区域和滑块按钮")
        ttk.Label(self, textvariable=self.status, foreground="#1a5276").pack(anchor=tk.W, padx=12)

        logf = ttk.LabelFrame(self, text="日志", padding=6)
        logf.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self.log = scrolledtext.ScrolledText(logf, height=10, font=("Consolas", 9))
        self.log.pack(fill=tk.BOTH, expand=True)

        self.bind("<F8>", lambda e: self.run_solve())

    def _log(self, msg: str) -> None:
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def _save_params(self) -> None:
        self.cfg["manual_distance"] = int(self.manual_dist.get())
        self.cfg["offset_x"] = int(self.offset_x.get())
        self.cfg["drag_duration_ms"] = int(self.duration.get())
        save_config(self.cfg)
        self._log("[*] 参数已保存")

    def _open_templates(self) -> None:
        import os

        TEMPLATES_DIR.mkdir(exist_ok=True)
        os.startfile(str(TEMPLATES_DIR))  # type: ignore[attr-defined]

    def _pick_region(self, title: str, on_save) -> None:
        self.status.set(title + " — 拖拽框选，Esc 取消")
        self.update()
        RegionPicker(lambda r: self.after(100, lambda: on_save(r)))

    def pick_captcha_region(self) -> None:
        def done(region: Region | None) -> None:
            if not region:
                return
            self.cfg["captcha_region"] = region.as_dict()
            save_config(self.cfg)
            path = TEMPLATES_DIR / "captcha_region_preview.png"
            TEMPLATES_DIR.mkdir(exist_ok=True)
            save_region_image(region, path)
            self._log(f"[OK] 验证码区域: {region.as_dict()}")
            self.status.set("已保存验证码区域")

        self._pick_region("框选整条滑块验证区域", done)

    def pick_slider_template(self) -> None:
        def done(region: Region | None) -> None:
            if not region:
                return
            TEMPLATES_DIR.mkdir(exist_ok=True)
            path = TEMPLATES_DIR / "slider_knob.png"
            save_region_image(region, path)
            self.cfg["slider_template"] = str(path)
            save_config(self.cfg)
            self._log(f"[OK] 滑块按钮模板: {path}")
            self.status.set("已保存滑块按钮模板")

        self._pick_region("框选滑块上的小方块按钮", done)

    def pick_bg_template(self) -> None:
        def done(region: Region | None) -> None:
            if not region:
                return
            TEMPLATES_DIR.mkdir(exist_ok=True)
            path = TEMPLATES_DIR / "slider_piece.png"
            save_region_image(region, path)
            self.cfg["bg_template"] = str(path)
            save_config(self.cfg)
            self._log(f"[OK] 滑块拼图块(可选): {path}")

        self._pick_region("框选拼图小图(可选，提高识别率)", done)

    def run_solve(self) -> None:
        self._save_params()
        self.status.set("执行中…请勿动鼠标")
        self._log("[*] 开始自动拖动…")

        def done(result) -> None:
            if result.ok:
                self._log(f"[OK] {result.message}")
                self.status.set("拖动完成 — 请看软件是否通过")
            else:
                self._log(f"[FAIL] {result.message}")
                self.status.set(result.message)
                messagebox.showwarning("未完成", result.message)

        def worker() -> None:
            result = solve_once(self.cfg)
            self.after(0, lambda: done(result))

        threading.Thread(target=worker, daemon=True).start()


def main() -> int:
    TEMPLATES_DIR.mkdir(exist_ok=True)
    SliderAutoApp().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
