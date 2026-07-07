#!/usr/bin/env python3
"""两步验证助手 — 按字选图 + 最慢动球。"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from verify_auto.click_util import click_screen

from slider_solver.screen_match import Region, save_region_image
from verify_auto.ball_slowest import find_slowest_moving_ball
from verify_auto.config import APP_DIR, LIBRARY_DIR, TEMPLATES_DIR, load_config, save_config
from verify_auto.learn import (
    learn_both_auto_pass,
    learn_step1_auto_pass,
    learn_step2_auto_motion,
)
from verify_auto.library_store import STEP1_DIR, STEP2_DIR, ensure_library, list_step1_keywords
from verify_auto.confirm_click import click_confirm_button
from verify_auto.locate_cache import invalidate_cache, start_prefetch
from verify_auto.pipeline import run_full_pipeline
from verify_auto.region_resolve import ResolveResult, resolve_regions
from verify_auto.step1_library import run_step1_library

APP_VERSION = "0.5.0"


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
        ensure_library()
        self._build()
        self._busy = threading.Lock()
        threading.Thread(target=self._warmup_ocr, daemon=True).start()
        start_prefetch(lambda: self.cfg)

    def _warmup_ocr(self) -> None:
        try:
            from verify_auto.ocr_util import warmup_ocr

            warmup_ocr()
            if self.cfg.get("layout_profile"):
                resolve_regions(self.cfg, step_hint=0, force_refresh=True)
            self.after(0, lambda: self.status.set("就绪（后台已预热，可直接点功能）"))
        except Exception:
            self.after(0, lambda: self.status.set("就绪"))

    def _resolve_cfg(self, step_hint: int = 0) -> ResolveResult:
        return resolve_regions(self.cfg, step_hint=step_hint)

    def _build(self) -> None:
        g = ttk.LabelFrame(self, text="你的做法：手动存图到词库 → 以后按图识别", padding=8)
        g.pack(fill=tk.X, padx=10, pady=4)
        for line in (
            "收录：你像平时一样过验证（选对 → 确定），工具自动识别文字和图片存进词库",
            "第1步：自动读提示词 + 识别你勾选的那张图 | 第2步：自动找最慢动球（不用手点）",
            "多收录几次后按 F8 全自动",
        ):
            ttk.Label(g, text=line, wraplength=700).pack(anchor=tk.W)

        lib = ttk.LabelFrame(self, text="词库 / 学习", padding=6)
        lib.pack(fill=tk.X, padx=10, pady=4)
        for text, cmd in (
            ("打开第1步词库", self.open_lib_step1),
            ("打开第2步词库", self.open_lib_step2),
            ("自动收录第1步", self.learn_step1_auto),
            ("自动收录第2步", self.learn_step2_auto),
            ("自动收录两步", self.learn_both_auto),
        ):
            ttk.Button(lib, text=text, command=cmd).pack(side=tk.LEFT, padx=3, pady=2)

        g2 = ttk.LabelFrame(self, text="自动过验证", padding=8)
        g2.pack(fill=tk.X, padx=10, pady=4)
        for line in (
            "第1步：按字选图 → 确定 | 第2步：在动球里选最慢的 → 确定",
        ):
            ttk.Label(g2, text=line).pack(anchor=tk.W)

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
            ("测试自动定位", self.test_auto_locate),
            ("仅第1步", self.run_step1_only),
            ("仅第2步", self.run_step2_only),
        ):
            ttk.Button(row2, text=text, command=cmd).pack(side=tk.LEFT, padx=4)

        opts = ttk.LabelFrame(self, text="参数", padding=8)
        opts.pack(fill=tk.X, padx=10)
        self.keyword = tk.StringVar(value=self.cfg.get("keyword_override") or "")
        self.frames = tk.IntVar(value=int(self.cfg.get("ball_frames") or 15))
        self.interval = tk.IntVar(value=int(self.cfg.get("ball_interval_ms") or 100))
        self.background_click = tk.BooleanVar(value=bool(self.cfg.get("background_click", True)))
        ttk.Label(opts, text="关键词(可选，OCR失败时填):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(opts, textvariable=self.keyword, width=12).grid(row=0, column=1, padx=4)
        ttk.Label(opts, text="采样帧:").grid(row=0, column=2, padx=(8, 0))
        ttk.Spinbox(opts, from_=8, to=30, textvariable=self.frames, width=5).grid(row=0, column=3)
        ttk.Label(opts, text="间隔ms:").grid(row=0, column=4)
        ttk.Spinbox(opts, from_=50, to=400, textvariable=self.interval, width=5).grid(row=0, column=5, padx=4)
        ttk.Checkbutton(opts, text="后台点击(不动鼠标)", variable=self.background_click).grid(
            row=1, column=0, columnspan=3, sticky=tk.W, pady=(6, 0)
        )
        ttk.Button(opts, text="保存", command=self._save).grid(row=0, column=6, padx=8)

        self.status = tk.StringVar(value="请先弹出验证小窗，再框选 4 个区域（只需一次）")
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
        self.cfg["background_click"] = bool(self.background_click.get())
        save_config(self.cfg)

    def open_lib_step1(self) -> None:
        ensure_library()
        import os
        import subprocess
        import sys

        path = str(STEP1_DIR)
        kws = list_step1_keywords()
        self._log(f"第1步词库: {path}  已有: {', '.join(kws) or '无'}")
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def open_lib_step2(self) -> None:
        ensure_library()
        import os
        import subprocess
        import sys

        path = str(STEP2_DIR)
        self._log(f"第2步词库: {path}")
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _resolve_or_warn(self, step_hint: int = 0):
        """同步定位（仅框选后立即用）。一般操作请走后台线程。"""
        resolved = self._resolve_cfg(step_hint)
        if not resolved.ok or not resolved.regions:
            messagebox.showerror("错误", resolved.message)
            return None
        self._log(resolved.message)
        return resolved.regions

    def test_auto_locate(self) -> None:
        self.status.set("已启动")
        self._log("[*] 测试自动定位…")

        def work():
            return self._resolve_cfg(step_hint=0)

        def done(r):
            if not r.ok or not r.regions:
                self._log(f"[FAIL] {r.message}")
                self.status.set(r.message)
                return
            a = r.regions
            self._log(
                f"[OK] {r.message}\n"
                f"  提示区 {a.prompt.as_dict()}\n"
                f"  网格区 {a.grid.as_dict()}\n"
                f"  球区域 {a.ball.as_dict()}"
            )
            self.status.set("自动定位成功")

        self._run_bg(work, done)

    def learn_step1_auto(self) -> None:
        self._save()
        self._log("[*] 自动收录第1步：请你在验证里选对图片 → 点确定")
        self._log("    （出现蓝色勾时会自动读文字并保存该图）")
        self.status.set("等待你选对…")

        def work():
            return learn_step1_auto_pass(
                self.cfg,
                keyword_override=self.keyword.get().strip(),
            )

        def done(r):
            self._log(("[OK] " if r.ok else "[FAIL] ") + r.message)
            self.status.set(r.message)

        self._run_bg(work, done)

    def learn_step2_auto(self) -> None:
        self._save()
        self._log("[*] 自动收录第2步：弹出第2步后自动找最慢动球")
        self.status.set("等待第2步界面…")

        def work():
            return learn_step2_auto_motion(
                self.cfg,
                ball_frames=int(self.frames.get()),
                ball_interval_ms=int(self.interval.get()),
            )

        def done(r):
            self._log(("[OK] " if r.ok else "[FAIL] ") + r.message)
            self.status.set(r.message)

        self._run_bg(work, done)

    def learn_both_auto(self) -> None:
        self._save()
        self._log("[*] 自动收录两步：请完整过一遍验证（第1步点对+确定 → 第2步等自动收录）")
        self.status.set("等待你过验证…")

        def work():
            return learn_both_auto_pass(
                self.cfg,
                keyword_override=self.keyword.get().strip(),
                ball_frames=int(self.frames.get()),
                ball_interval_ms=int(self.interval.get()),
            )

        def done(r):
            self._log(("[OK] " if r.ok else "[FAIL] ") + r.message)
            self.status.set(r.message)

        self._run_bg(work, done)

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
        self._log(f"[OK] 已保存区域，正在后台更新布局…")
        invalidate_cache()

        def work() -> None:
            from verify_auto.layout_profile import update_layout_profile

            if update_layout_profile(self.cfg):
                save_config(self.cfg)
                self.after(0, lambda: self._log("[OK] 自动定位布局已更新"))

        threading.Thread(target=work, daemon=True).start()

    def _click_confirm(self, search: Region | None = None) -> bool:
        return click_confirm_button(self.cfg, search)

    def run_full(self) -> None:
        self._save()
        self._log("[*] 一键全流程…")
        self.status.set("已启动")

        def work():
            return run_full_pipeline(self.cfg, keyword_override=self.keyword.get().strip())

        self._run_bg(work)

    def run_step1_only(self) -> None:
        self._save()
        self._log("[*] 第1步…")
        self.status.set("已启动")

        def work():
            resolved = self._resolve_cfg(step_hint=1)
            if not resolved.ok or not resolved.regions:
                return resolved
            areas = resolved.regions
            r = run_step1_library(
                areas.prompt,
                areas.grid,
                keyword_override=self.keyword.get().strip(),
                min_score=float(self.cfg.get("step1_min_score") or 0.72),
            )
            confirm_ok = False
            if r.ok:
                bg = bool(self.cfg.get("background_click", True))
                click_screen(r.click_x, r.click_y, background=bg)
                confirm_ok = click_confirm_button(self.cfg, areas.search)
            return (resolved, r, confirm_ok)

        def done(payload):
            if isinstance(payload, ResolveResult):
                self._log(f"[FAIL] {payload.message}")
                self.status.set(payload.message)
                return
            resolved, r, confirm_ok = payload
            self._log(resolved.message)
            self._log(("[OK] " if r.ok else "[FAIL] ") + r.message)
            if r.ok and not confirm_ok:
                self._log("[FAIL] 未找到确定按钮")
            self.status.set(r.message)

        self._run_bg(work, done)

    def run_step2_only(self) -> None:
        self._save()
        self._log("[*] 第2步…")
        self.status.set("已启动")

        def work():
            resolved = self._resolve_cfg(step_hint=2)
            if not resolved.ok or not resolved.regions:
                return resolved
            r = find_slowest_moving_ball(
                resolved.regions.ball,
                frames=int(self.frames.get()),
                interval_ms=int(self.interval.get()),
            )
            confirm_ok = False
            if r.ok:
                bg = bool(self.cfg.get("background_click", True))
                click_screen(r.click_x, r.click_y, background=bg)
                confirm_ok = click_confirm_button(self.cfg, resolved.regions.search)
            return (resolved, r, confirm_ok)

        def done(payload):
            if isinstance(payload, ResolveResult):
                self._log(f"[FAIL] {payload.message}")
                self.status.set(payload.message)
                return
            resolved, r, confirm_ok = payload
            self._log(resolved.message)
            for mid, mv in r.movers:
                self._log(f"  动球 {mid} 位移={mv:.1f}px (静止装饰约 {r.stationary_count} 个忽略)")
            if not r.ok:
                self._log(f"[FAIL] {r.message}")
                self.status.set(r.message)
                return
            self._log(f"[OK] {r.message}")
            if not confirm_ok:
                self._log("[FAIL] 未找到确定按钮")
            self.status.set(r.message)

        self._run_bg(work, done)

    def _run_bg(self, fn, done=None) -> None:
        if not self._busy.acquire(blocking=False):
            self._log("[!] 上一任务还在跑，请稍候")
            return

        def worker():
            try:
                result = fn()
            except Exception as exc:
                result = exc
            finally:
                self._busy.release()
            self.after(0, lambda r=result: wrap(r))

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

        threading.Thread(target=worker, daemon=True, name="verify-task").start()


def main() -> int:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    VerifyApp().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
