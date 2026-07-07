#!/usr/bin/env python3
"""两步验证助手 — 按字选图 + 最慢动球。"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

import pyautogui

from slider_solver.screen_match import Region, save_region_image
from verify_auto.ball_slowest import find_slowest_moving_ball
from verify_auto.config import APP_DIR, TEMPLATES_DIR, load_config, save_config
from verify_auto.pipeline import run_full_pipeline
from verify_auto.step1_pick import run_step1

APP_VERSION = "0.2.0"


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
        self.geometry("740x600")
        self.cfg = load_config()
        self._build()

    def _build(self) -> None:
        g = ttk.LabelFrame(self, text="你的验证（同一窗口两步）", padding=8)
        g.pack(fill=tk.X, padx=10, pady=4)
        for line in (
            "第1步：选择最符合描述的图片（如「兔子」）→ 确定",
            "第2步：很多不动的装饰球 + 少数会动的球 → 点动得最慢的那个 → 确定",
            "首次使用：按下面按钮各框选一次区域，然后点「一键全自动 F8」",
        ):
            ttk.Label(g, text=line, wraplength=700).pack(anchor=tk.W)

        row = ttk.Frame(self, padding=6)
        row.pack(fill=tk.X)
        for text, cmd in (
            ("提示文字区", self.pick_prompt),
            ("图片网格区", self.pick_grid),
            ("第2步球区域", self.pick_ball),
            ("确定按钮", self.pick_confirm),
        ):
            ttk.Button(row, text=text, command=cmd).pack(side=tk.LEFT, padx=2)

        row2 = ttk.Frame(self, padding=6)
        row2.pack(fill=tk.X)
        for text, cmd in (
            ("一键全自动 F8", self.run_full),
            ("仅第1步", self.run_step1_only),
            ("仅第2步", self.run_step2_only),
        ):
            ttk.Button(row2, text=text, command=cmd).pack(side=tk.LEFT, padx=4)

        opts = ttk.LabelFrame(self, text="参数", padding=8)
        opts.pack(fill=tk.X, padx=10)
        self.keyword = tk.StringVar(value=self.cfg.get("keyword_override") or "")
        self.frames = tk.IntVar(value=int(self.cfg.get("ball_frames") or 15))
        self.interval = tk.IntVar(value=int(self.cfg.get("ball_interval_ms") or 100))
        ttk.Label(opts, text="关键词(可选，OCR失败时填):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(opts, textvariable=self.keyword, width=12).grid(row=0, column=1, padx=4)
        ttk.Label(opts, text="采样帧:").grid(row=0, column=2, padx=(8, 0))
        ttk.Spinbox(opts, from_=8, to=30, textvariable=self.frames, width=5).grid(row=0, column=3)
        ttk.Label(opts, text="间隔ms:").grid(row=0, column=4)
        ttk.Spinbox(opts, from_=50, to=400, textvariable=self.interval, width=5).grid(row=0, column=5, padx=4)
        ttk.Button(opts, text="保存", command=self._save).grid(row=0, column=6, padx=8)

        self.status = tk.StringVar(value="请先框选 4 个区域")
        ttk.Label(self, textvariable=self.status, foreground="#1a5276").pack(anchor=tk.W, padx=12)

        logf = ttk.LabelFrame(self, text="日志", padding=6)
        logf.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self.log = scrolledtext.ScrolledText(logf, height=14, font=("Consolas", 9))
        self.log.pack(fill=tk.BOTH, expand=True)
        self.bind("<F8>", lambda e: self.run_full())

    def _log(self, msg: str) -> None:
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def _save(self) -> None:
        self.cfg["keyword_override"] = self.keyword.get().strip()
        self.cfg["ball_frames"] = int(self.frames.get())
        self.cfg["ball_interval_ms"] = int(self.interval.get())
        save_config(self.cfg)

    def _pick(self, title: str, setter) -> None:
        def done(r: Region | None) -> None:
            if r:
                setter(r)
                self._log(f"[OK] {title}: {r.as_dict()}")

        self.status.set(title)
        RegionPicker(lambda x: self.after(100, lambda: done(x)))

    def pick_prompt(self) -> None:
        self._pick("框选顶部提示文字（含「选择最符合…」）", lambda r: self._set("prompt_region", r))

    def pick_grid(self) -> None:
        self._pick("框选 2×3 图片网格（不要含确定按钮）", lambda r: self._set("grid_region", r))

    def pick_ball(self) -> None:
        self._pick("框选第2步球区域（含动球和不动装饰球）", lambda r: self._set("step2_ball_region", r))

    def pick_confirm(self) -> None:
        def done(r: Region | None) -> None:
            if not r:
                return
            TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
            path = TEMPLATES_DIR / "confirm.png"
            save_region_image(r, path)
            self.cfg["confirm_template"] = str(path)
            save_config(self.cfg)
            self._log(f"[OK] 确定按钮: {path}")

        self.status.set("框选蓝色「确定」按钮")
        RegionPicker(lambda x: self.after(100, lambda: done(x)))

    def _set(self, key: str, r: Region) -> None:
        self.cfg[key] = r.as_dict()
        save_config(self.cfg)

    def _click_confirm(self) -> bool:
        tpl = self.cfg.get("confirm_template") or ""
        if not tpl:
            return False
        from slider_solver.screen_match import find_on_screen
        import cv2
        import numpy as np

        m = find_on_screen(tpl, None, threshold=0.55)
        if not m:
            return False
        img = cv2.imdecode(np.fromfile(tpl, dtype=np.uint8), cv2.IMREAD_COLOR)
        pyautogui.click(m.screen_x + img.shape[1] // 2, m.screen_y + img.shape[0] // 2)
        return True

    def run_full(self) -> None:
        self._save()
        self._log("[*] 一键全流程…")
        self._run_bg(lambda: run_full_pipeline(self.cfg, keyword_override=self.keyword.get().strip()))

    def run_step1_only(self) -> None:
        self._save()
        pr = Region.from_dict(self.cfg.get("prompt_region"))
        gr = Region.from_dict(self.cfg.get("grid_region"))
        if not pr or not gr:
            messagebox.showerror("错误", "请先框选提示区和网格区")
            return

        def work():
            r = run_step1(pr, gr, keyword_override=self.keyword.get().strip())
            if r.ok:
                pyautogui.click(r.click_x, r.click_y)
            return r

        def done(r):
            self._log(("[OK] " if r.ok else "[FAIL] ") + r.message)
            if r.ok:
                self._click_confirm()

        self._run_bg(work, done)

    def run_step2_only(self) -> None:
        self._save()
        ball = Region.from_dict(self.cfg.get("step2_ball_region"))
        if not ball:
            messagebox.showerror("错误", "请先框选球区域")
            return
        self._log("[*] 第2步：只追踪会动的球…")

        def work():
            return find_slowest_moving_ball(
                ball, frames=int(self.frames.get()), interval_ms=int(self.interval.get())
            )

        def done(r):
            for mid, mv in r.movers:
                self._log(f"  动球 {mid} 位移={mv:.1f}px (静止装饰约 {r.stationary_count} 个忽略)")
            if not r.ok:
                self._log(f"[FAIL] {r.message}")
                return
            self._log(f"[OK] {r.message}")
            pyautogui.click(r.click_x, r.click_y)
            self._click_confirm()

        self._run_bg(work, done)

    def _run_bg(self, fn, done=None) -> None:
        def worker():
            try:
                return fn()
            except Exception as exc:
                return exc

        def wrap(result):
            if isinstance(result, Exception):
                self._log(f"[ERR] {result}")
                self.status.set(str(result))
            elif done:
                done(result)
            else:
                ok = getattr(result, "ok", True)
                self._log(("[OK] " if ok else "[FAIL] ") + getattr(result, "message", str(result)))
                self.status.set(getattr(result, "message", "完成"))

        threading.Thread(target=lambda: self.after(0, lambda: wrap(worker())), daemon=True).start()


def main() -> int:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    VerifyApp().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
