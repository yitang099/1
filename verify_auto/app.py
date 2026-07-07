#!/usr/bin/env python3
"""两步验证助手 v0.1 — 最慢球 + 按字选图(开发中)。"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

import pyautogui

from slider_solver.screen_match import Region, save_region_image
from verify_auto.ball_slowest import find_slowest_ball
from verify_auto.config import APP_DIR, load_config, save_config

APP_VERSION = "0.1.0"


class RegionPicker:
    def __init__(self, on_done) -> None:
        self.on_done = on_done
        self.root = tk.Toplevel()
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.25)
        self.root.configure(bg="black")
        self.canvas = tk.Canvas(self.root, cursor="cross", bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.sx = self.sy = 0
        self.rect = None
        self.canvas.bind("<ButtonPress-1>", self._down)
        self.canvas.bind("<B1-Motion>", self._move)
        self.canvas.bind("<ButtonRelease-1>", self._up)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

    def _down(self, e) -> None:
        self.sx, self.sy = e.x, e.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=2)

    def _move(self, e) -> None:
        self.canvas.coords(self.rect, self.sx, self.sy, e.x, e.y)

    def _up(self, e) -> None:
        x1, y1, x2, y2 = self.sx, self.sy, e.x, e.y
        self.root.destroy()
        w, h = abs(x2 - x1), abs(y2 - y1)
        if w < 10 or h < 10:
            self.on_done(None)
        else:
            self.on_done(Region(min(x1, x2), min(y1, y2), w, h))


class VerifyApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"两步验证助手 v{APP_VERSION}")
        self.geometry("720x560")
        self.cfg = load_config()
        self._build()

    def _build(self) -> None:
        g = ttk.LabelFrame(self, text="你的验证流程（不是滑块）", padding=8)
        g.pack(fill=tk.X, padx=10, pady=6)
        for line in (
            "第1步：按字选对应图片 — 需要 OCR/图像匹配（请发截图我来接）",
            "第2步：点移动最慢的球 → 再点确定 — 本工具已支持自动找最慢球",
        ):
            ttk.Label(g, text=line, wraplength=680).pack(anchor=tk.W)

        row = ttk.Frame(self, padding=8)
        row.pack(fill=tk.X)
        for text, cmd in (
            ("框选第2步球区域", self.pick_ball_region),
            ("框选确定按钮", self.pick_confirm),
            ("找最慢球并点击", self.run_ball_step),
            ("只分析不点击", self.analyze_only),
        ):
            ttk.Button(row, text=text, command=cmd).pack(side=tk.LEFT, padx=4)

        opts = ttk.LabelFrame(self, text="第2步参数", padding=8)
        opts.pack(fill=tk.X, padx=10)
        self.frames = tk.IntVar(value=int(self.cfg.get("ball_frames") or 12))
        self.interval = tk.IntVar(value=int(self.cfg.get("ball_interval_ms") or 120))
        ttk.Label(opts, text="采样帧数:").grid(row=0, column=0, sticky=tk.W)
        ttk.Spinbox(opts, from_=6, to=30, textvariable=self.frames, width=6).grid(row=0, column=1, padx=4)
        ttk.Label(opts, text="帧间隔ms:").grid(row=0, column=2, sticky=tk.W, padx=(8, 0))
        ttk.Spinbox(opts, from_=50, to=500, textvariable=self.interval, width=6).grid(row=0, column=3, padx=4)
        ttk.Button(opts, text="保存", command=self._save).grid(row=0, column=4, padx=8)

        self.status = tk.StringVar(value="请先框选球区域")
        ttk.Label(self, textvariable=self.status, foreground="#1a5276").pack(anchor=tk.W, padx=12)

        logf = ttk.LabelFrame(self, text="日志", padding=6)
        logf.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self.log = scrolledtext.ScrolledText(logf, height=12, font=("Consolas", 9))
        self.log.pack(fill=tk.BOTH, expand=True)

    def _log(self, msg: str) -> None:
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def _save(self) -> None:
        self.cfg["ball_frames"] = int(self.frames.get())
        self.cfg["ball_interval_ms"] = int(self.interval.get())
        save_config(self.cfg)

    def _pick(self, title: str, key: str) -> None:
        def done(r: Region | None) -> None:
            if not r:
                return
            self.cfg[key] = r.as_dict()
            save_config(self.cfg)
            self._log(f"[OK] {key}: {r.as_dict()}")

        self.status.set(title)
        RegionPicker(lambda x: self.after(100, lambda: done(x)))

    def pick_ball_region(self) -> None:
        self._pick("框住所有彩色球（不要包确定按钮）", "step2_ball_region")

    def pick_confirm(self) -> None:
        def done(r: Region | None) -> None:
            if not r:
                return
            path = APP_DIR / "templates" / "confirm.png"
            path.parent.mkdir(exist_ok=True)
            save_region_image(r, path)
            self.cfg["confirm_template"] = str(path)
            save_config(self.cfg)
            self._log(f"[OK] 确定按钮模板: {path}")

        self.status.set("框选「确定」按钮")
        RegionPicker(lambda x: self.after(100, lambda: done(x)))

    def analyze_only(self) -> None:
        self._run_ball(click=False)

    def run_ball_step(self) -> None:
        self._run_ball(click=True)

    def _run_ball(self, *, click: bool) -> None:
        self._save()
        region = Region.from_dict(self.cfg.get("step2_ball_region"))
        if not region:
            messagebox.showerror("错误", "请先框选球区域")
            return
        self._log("[*] 采样中，请看球在动…")
        self.status.set("采样中…")

        def work():
            return find_slowest_ball(
                region,
                frames=int(self.frames.get()),
                interval_ms=int(self.interval.get()),
            )

        def done(result) -> None:
            for name, spd in result.speeds:
                self._log(f"  {name} 移动量={spd:.1f}")
            if not result.ok:
                self._log(f"[FAIL] {result.message}")
                self.status.set(result.message)
                return
            self._log(f"[OK] {result.message}")
            if click:
                pyautogui.click(result.click_x, result.click_y)
                self._log(f"[*] 已点击球 ({result.click_x},{result.click_y})")
                import time

                time.sleep(0.4)
                self._click_confirm()
            else:
                self.status.set(f"最慢球在 ({result.click_x},{result.click_y})")

        threading.Thread(target=lambda: self.after(0, lambda: done(work())), daemon=True).start()

    def _click_confirm(self) -> None:
        tpl = self.cfg.get("confirm_template") or ""
        if not tpl:
            self._log("[WARN] 未框选确定按钮，请手动点确定")
            return
        from slider_solver.screen_match import find_on_screen

        m = find_on_screen(tpl, None, threshold=0.55)
        if not m:
            self._log("[WARN] 未找到确定按钮")
            return
        import numpy as np
        import cv2

        data = np.fromfile(tpl, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        cx = m.screen_x + img.shape[1] // 2
        cy = m.screen_y + img.shape[0] // 2
        pyautogui.click(cx, cy)
        self._log(f"[*] 已点确定 ({cx},{cy})")


def main() -> int:
    VerifyApp().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
