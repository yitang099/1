#!/usr/bin/env python3
"""两步验证助手 — 按字选图 + 最慢动球。"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from verify_auto.click_util import click_screen

from slider_solver.screen_match import Region, save_region_image
from verify_auto.ball_slowest import find_slowest_moving_ball
from verify_auto.config import APP_DIR, LIBRARY_DIR, TEMPLATES_DIR, load_config, save_config
from verify_auto.learn import learn_watch_loop
from verify_auto.confirm_click import click_confirm_button
from verify_auto.locate_cache import invalidate_cache, stop_prefetch
from verify_auto.pipeline import run_full_pipeline
from verify_auto.region_resolve import ResolveResult, resolve_regions
from verify_auto.library_store import STEP1_DIR, STEP2_DIR, ensure_library
from verify_auto.manual_import import (
    ManualImportResult,
    import_step1_file,
    import_step1_region,
    import_step2_file,
    import_step2_region,
    library_summary,
)
from verify_auto.fast_agent import run_fast_agent
from verify_auto.library_cache import library_stats, load_library_cache
from verify_auto.manual_step2 import start_step2_click_learn
from verify_auto.step1_library import run_step1_library

APP_VERSION = "0.8.1"


class KeywordDialog(tk.Toplevel):
    """弹窗：填写图片关键词/标签。"""

    def __init__(
        self,
        master,
        *,
        title: str,
        prompt: str,
        default: str = "",
        hint: str = "",
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.result: str | None = None
        self.transient(master)
        self.grab_set()

        ttk.Label(self, text=prompt, padding=(12, 10, 12, 4)).pack(anchor=tk.W)
        if hint:
            ttk.Label(self, text=hint, foreground="#555", wraplength=360).pack(anchor=tk.W, padx=12)
        self.var = tk.StringVar(value=default)
        ent = ttk.Entry(self, textvariable=self.var, width=36)
        ent.pack(padx=12, pady=8)
        ent.focus_set()
        ent.select_range(0, tk.END)

        row = ttk.Frame(self, padding=12)
        row.pack(fill=tk.X)
        ttk.Button(row, text="确定", command=self._ok).pack(side=tk.RIGHT, padx=4)
        ttk.Button(row, text="取消", command=self._cancel).pack(side=tk.RIGHT)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())

    def _ok(self) -> None:
        v = self.var.get().strip()
        if not v:
            messagebox.showwarning("提示", "请填写关键词/标签", parent=self)
            return
        self.result = v
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()

    @classmethod
    def ask(cls, master, **kwargs) -> str | None:
        dlg = cls(master, **kwargs)
        master.wait_window(dlg)
        return dlg.result


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
        self.geometry("760x680")
        self.cfg = load_config()
        ensure_library()
        self._build()
        self._busy = threading.Lock()
        self._learn_stop: threading.Event | None = None
        self._learn_thread: threading.Thread | None = None
        self.lib_info = tk.StringVar(value="词库加载中…")
        threading.Thread(target=self._preload_library, daemon=True).start()
        threading.Thread(target=self._warmup_ocr, daemon=True).start()
        stop_prefetch()

    def _preload_library(self) -> None:
        try:
            load_library_cache()
            s = library_stats()
            msg = f"词库：第1步 {s['step1_images']} 张/{s['step1_keywords']} 词 | 第2步慢球 {s['step2_slow_images']} 张"
            self.after(0, lambda: (self.lib_info.set(msg), self.status.set("就绪 — 弹出验证码后按 F9 一键启动")))
        except Exception:
            self.after(0, lambda: self.lib_info.set("词库加载失败"))

    def _warmup_ocr(self) -> None:
        try:
            from verify_auto.ocr_util import warmup_ocr

            warmup_ocr()
            self.after(0, lambda: self.status.set("就绪（低占用模式，点「开始持续收录」）"))
        except Exception:
            self.after(0, lambda: self.status.set("就绪"))

    def _resolve_cfg(self, step_hint: int = 0) -> ResolveResult:
        return resolve_regions(self.cfg, step_hint=step_hint)

    def _build(self) -> None:
        top = ttk.LabelFrame(self, text="⚡ 词库极速 — 一键过验证", padding=10)
        top.pack(fill=tk.X, padx=10, pady=6)
        ttk.Label(
            top,
            text="根据你收录的案例：快速找窗 → 按关键词匹配图片 → 自动过验证",
            wraplength=700,
        ).pack(anchor=tk.W)
        row_top = ttk.Frame(top)
        row_top.pack(fill=tk.X, pady=6)
        fast_btn = ttk.Button(row_top, text="▶ 一键启动 F9", command=self.run_fast_agent)
        fast_btn.pack(side=tk.LEFT, padx=4)
        ttk.Label(top, textvariable=self.lib_info, foreground="#1a5276").pack(anchor=tk.W)

        g = ttk.LabelFrame(self, text="手动截图收录（自己框图 + 填关键字）", padding=8)
        g.pack(fill=tk.X, padx=10, pady=4)
        for line in (
            "第1步：框选验证码里【正确的那一张小图】→ 填关键词（如 柠檬）→ 自动存入词库",
            "第2步（推荐）：点「截全图→点慢球」→ 框所有球区域 → 再点最慢的那个球",
            "第2步会自动截取全景里每个球，你点的那个保存为「慢球」",
        ):
            ttk.Label(g, text=line, wraplength=720).pack(anchor=tk.W)

        manual = ttk.Frame(g)
        manual.pack(fill=tk.X, pady=(6, 0))
        for text, cmd in (
            ("第1步：框选截图", self.manual_capture_step1),
            ("从文件导入第1步", self.manual_file_step1),
            ("第2步：截全图→点慢球", self.manual_step2_click_learn),
            ("第2步：框选截图", self.manual_capture_step2),
            ("从文件导入第2步", self.manual_file_step2),
        ):
            ttk.Button(manual, text=text, command=cmd).pack(side=tk.LEFT, padx=3, pady=2)

        lib = ttk.LabelFrame(self, text="词库 / 自动收录", padding=6)
        lib.pack(fill=tk.X, padx=10, pady=4)
        for text, cmd in (
            ("打开第1步词库", self.open_lib_step1),
            ("打开第2步词库", self.open_lib_step2),
            ("开始持续收录", self.toggle_learn_watch),
        ):
            ttk.Button(lib, text=text, command=cmd).pack(side=tk.LEFT, padx=3, pady=2)
        ttk.Label(lib, text="持续收录 = 你手动过验证时自动存图（可选）", foreground="#555").pack(
            anchor=tk.W, pady=(4, 0)
        )

        g_old = ttk.LabelFrame(self, text="高级：框选区域（F8 传统模式需要）", padding=6)
        g_old.pack(fill=tk.X, padx=10, pady=2)
        ttk.Label(
            g_old,
            text="F9 一键过验证一般不用框选。只有 F8 或收录不准时才需要框 5 项区域。",
            foreground="#555",
            wraplength=700,
        ).pack(anchor=tk.W)

        g2 = ttk.LabelFrame(self, text="备用模式", padding=8)
        g2.pack(fill=tk.X, padx=10, pady=4)
        for line in (
            "词库匹配失败时可用：强化AI(F10) / 传统F8",
        ):
            ttk.Label(g2, text=line).pack(anchor=tk.W)

        row = ttk.Frame(self, padding=6)
        row.pack(fill=tk.X)
        for text, cmd in (
            ("第1步文字", self.pick_step1_prompt),
            ("图片网格区", self.pick_grid),
            ("第2步文字", self.pick_step2_prompt),
            ("第2步球区域", self.pick_ball),
            ("确定按钮", self.pick_confirm),
        ):
            ttk.Button(row, text=text, command=cmd).pack(side=tk.LEFT, padx=2)

        row2 = ttk.Frame(self, padding=6)
        row2.pack(fill=tk.X)
        for text, cmd in (
            ("强化AI F10", self.run_ai_agent),
            ("传统全自动 F8", self.run_full),
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

        ai = ttk.LabelFrame(self, text="AI 代理（可选视觉 API 增强第1步选图）", padding=8)
        ai.pack(fill=tk.X, padx=10, pady=4)
        self.ai_enabled = tk.BooleanVar(value=bool(self.cfg.get("ai_enabled", False)))
        self.ai_api_key = tk.StringVar(value=self.cfg.get("ai_api_key") or "")
        self.ai_base_url = tk.StringVar(value=self.cfg.get("ai_base_url") or "https://api.openai.com/v1")
        self.ai_model = tk.StringVar(value=self.cfg.get("ai_model") or "gpt-4o-mini")
        ttk.Checkbutton(ai, text="启用 AI（无 API 也可用内置规则）", variable=self.ai_enabled).grid(
            row=0, column=0, columnspan=2, sticky=tk.W
        )
        ttk.Label(ai, text="API Key:").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(ai, textvariable=self.ai_api_key, width=28, show="*").grid(row=1, column=1, padx=4, sticky=tk.W)
        ttk.Label(ai, text="接口:").grid(row=1, column=2, padx=(8, 0))
        ttk.Entry(ai, textvariable=self.ai_base_url, width=22).grid(row=1, column=3, padx=4)
        ttk.Label(ai, text="模型:").grid(row=2, column=0, sticky=tk.W)
        ttk.Entry(ai, textvariable=self.ai_model, width=18).grid(row=2, column=1, padx=4, sticky=tk.W)
        ttk.Label(
            ai,
            text="不填 Key 也能用：自动找验证窗 + OCR 判断步骤 + 词库选图",
            foreground="#555",
        ).grid(row=2, column=2, columnspan=2, sticky=tk.W, padx=8)

        self.status = tk.StringVar(value="词库加载中…")
        ttk.Label(self, textvariable=self.status, foreground="#1a5276").pack(anchor=tk.W, padx=12)

        logf = ttk.LabelFrame(self, text="日志", padding=6)
        logf.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self.log = scrolledtext.ScrolledText(logf, height=14, font=("Consolas", 9))
        self.log.pack(fill=tk.BOTH, expand=True)
        self.bind("<F8>", lambda e: self.run_full())
        self.bind("<F9>", lambda e: self.run_fast_agent())
        self.bind("<F10>", lambda e: self.run_ai_agent())

    def _log(self, msg: str) -> None:
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def _save(self) -> None:
        self.cfg["keyword_override"] = self.keyword.get().strip()
        self.cfg["ball_frames"] = int(self.frames.get())
        self.cfg["ball_interval_ms"] = int(self.interval.get())
        self.cfg["background_click"] = bool(self.background_click.get())
        self.cfg["ai_enabled"] = bool(self.ai_enabled.get())
        self.cfg["ai_api_key"] = self.ai_api_key.get().strip()
        self.cfg["ai_base_url"] = self.ai_base_url.get().strip()
        self.cfg["ai_model"] = self.ai_model.get().strip()
        save_config(self.cfg)

    def _ask_keyword_step1(self, default: str = "") -> str | None:
        return KeywordDialog.ask(
            self,
            title="第1步 — 填写关键词",
            prompt="这张图对应验证码提示词是什么？",
            default=default or self.keyword.get().strip(),
            hint="例：柠檬、兔子、汽车。会保存到 library/step1/关键词/ 文件夹",
        )

    def _ask_keyword_step2(self, default: str = "动球") -> str | None:
        return KeywordDialog.ask(
            self,
            title="第2步 — 填写标签",
            prompt="这张球图是什么类型？",
            default=default,
            hint="例：动球（会动的）、慢球、装饰球。会保存到 library/step2/tags/标签/",
        )

    def _after_manual_import(self, r) -> None:
        if r.ok:
            load_library_cache(force=True)
            s = library_stats()
            self.lib_info.set(
                f"词库：第1步 {s['step1_images']} 张/{s['step1_keywords']} 词 | 第2步慢球 {s['step2_slow_images']} 张"
            )
            self._log(f"[OK] {r.message}")
            self._log(f"    路径: {r.path}")
            self._log(library_summary())
            self.status.set(r.message)
        else:
            self._log(f"[FAIL] {r.message}")
            self.status.set(r.message)

    def run_fast_agent(self) -> None:
        self._save()
        self._log("[*] 词库极速启动…")
        self.status.set("极速运行中")

        def work():
            def progress(msg: str) -> None:
                self.after(0, lambda m=msg: self._log(m))

            return run_fast_agent(
                self.cfg,
                keyword_override=self.keyword.get().strip(),
                on_progress=progress,
            )

        def done(r):
            self._log(("[OK] " if r.ok else "[FAIL] ") + r.message)
            self.status.set(r.message)

        self._run_bg(work, done)

    def manual_capture_step1(self) -> None:
        def on_region(region: Region | None) -> None:
            if not region:
                return
            kw = self._ask_keyword_step1()
            if not kw:
                self._log("[!] 已取消收录")
                return
            r = import_step1_region(region, kw)
            self._after_manual_import(r)

        self.status.set("请框选第1步【正确的那一张小图】（只框一张，不要框整个网格）")
        self._log("[*] 请框选第1步正确图片…")
        RegionPicker(lambda x: self.after(100, lambda: on_region(x)))

    def manual_step2_click_learn(self) -> None:
        if not self._busy.acquire(blocking=False):
            self._log("[!] 上一任务还在跑，请稍候")
            return

        def on_region(region: Region | None) -> None:
            if not region:
                self._busy.release()
                return

            self._log("[*] 已框选球区，正在截全景并识别所有球…")
            self.status.set("截图中…随后请点击最慢的球")

            def progress(msg: str) -> None:
                self.after(0, lambda m=msg: self._log(m))

            def done(r: ManualImportResult) -> None:
                self._busy.release()
                self._after_manual_import(r)

            start_step2_click_learn(region, on_done=lambda r: self.after(0, lambda: done(r)), on_progress=progress)

        self.status.set("请框住第2步【所有球】所在区域（含全部大球小球）")
        RegionPicker(lambda x: self.after(100, lambda: on_region(x)))

    def manual_capture_step2(self) -> None:
        def on_region(region: Region | None) -> None:
            if not region:
                return
            tag = self._ask_keyword_step2()
            if not tag:
                self._log("[!] 已取消收录")
                return
            r = import_step2_region(region, tag)
            self._after_manual_import(r)

        self.status.set("请框选第2步【会动的球】（小圆球，不要框大装饰球）")
        self._log("[*] 请框选第2步动球截图…")
        RegionPicker(lambda x: self.after(100, lambda: on_region(x)))

    def manual_file_step1(self) -> None:
        path = filedialog.askopenfilename(
            title="选择第1步正确图片",
            filetypes=[("图片", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"), ("所有", "*.*")],
        )
        if not path:
            return
        kw = self._ask_keyword_step1()
        if not kw:
            return
        self._after_manual_import(import_step1_file(path, kw))

    def manual_file_step2(self) -> None:
        path = filedialog.askopenfilename(
            title="选择第2步球图片",
            filetypes=[("图片", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"), ("所有", "*.*")],
        )
        if not path:
            return
        tag = self._ask_keyword_step2()
        if not tag:
            return
        self._after_manual_import(import_step2_file(path, tag))

    def open_lib_step1(self) -> None:
        ensure_library()
        import os
        import subprocess
        import sys

        path = str(STEP1_DIR)
        self._log(f"第1步词库: {path}")
        self._log(library_summary())
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
        self._log(f"第2步词库: {path}  (手动收录在 tags/ 子文件夹)")
        self._log(library_summary())
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
                f"  第1步文字 {a.step1_prompt.as_dict()}\n"
                f"  第2步文字 {a.step2_prompt.as_dict()}\n"
                f"  网格区 {a.grid.as_dict()}\n"
                f"  球区域 {a.ball.as_dict()}"
            )
            self.status.set("自动定位成功")

        self._run_bg(work, done)

    def toggle_learn_watch(self) -> None:
        if self._learn_thread and self._learn_thread.is_alive():
            if self._learn_stop:
                self._learn_stop.set()
            self._log("[*] 正在停止收录…")
            self.status.set("正在停止…")
            return

        self._save()
        stop_prefetch()
        self._learn_stop = threading.Event()

        def progress(msg: str) -> None:
            self.after(0, lambda m=msg: self._log(m))

        def work():
            return learn_watch_loop(
                self.cfg,
                self._learn_stop,
                keyword_override=self.keyword.get().strip(),
                on_progress=progress,
            )

        def done(r):
            self._learn_thread = None
            self._log(("[OK] " if r.ok else "[!] ") + r.message)
            self.status.set("收录已停止" if r.ok else r.message)

        self._log("[*] 持续收录已开始：请正常过验证（可连续收多张）")
        self.status.set("收录中…")

        def runner():
            try:
                result = work()
            except Exception as exc:
                self.after(0, lambda: (self._log(f"[ERR] {exc}"), self.status.set(str(exc))))
                return
            self.after(0, lambda: done(result))

        self._learn_thread = threading.Thread(target=runner, daemon=True, name="learn-watch")
        self._learn_thread.start()

    def _pick(self, title: str, setter) -> None:
        def done(r: Region | None) -> None:
            if r:
                setter(r)
                self._log(f"[OK] {title}: {r.as_dict()}")

        self.status.set(title)
        RegionPicker(lambda x: self.after(100, lambda: done(x)))

    def pick_step1_prompt(self) -> None:
        self._pick(
            "框选第1步提示（弹出第1步时框：选择最符合…含关键词）",
            lambda r: self._set_prompt("step1_prompt_region", r, sync_legacy=True),
        )

    def pick_step2_prompt(self) -> None:
        self._pick(
            "框选第2步提示（弹出第2步时框：请点击运动最慢的元素）",
            lambda r: self._set_prompt("step2_prompt_region", r),
        )

    def pick_prompt(self) -> None:
        self.pick_step1_prompt()

    def pick_grid(self) -> None:
        self._pick("框选 2×3 图片网格（不要含确定按钮）", lambda r: self._set("grid_region", r))

    def pick_ball(self) -> None:
        self._pick("框选第2步球区域（与图片网格同位置，稍大一点）", lambda r: self._set("step2_ball_region", r))

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

    def _set_prompt(self, key: str, r: Region, *, sync_legacy: bool = False) -> None:
        self.cfg[key] = r.as_dict()
        if sync_legacy:
            self.cfg["prompt_region"] = r.as_dict()
        save_config(self.cfg)
        self._log(f"[OK] 已保存区域，正在后台更新布局…")
        invalidate_cache()

        def work() -> None:
            from verify_auto.layout_profile import update_layout_profile

            if update_layout_profile(self.cfg):
                save_config(self.cfg)
                self.after(0, lambda: self._log("[OK] 自动定位布局已更新"))

        threading.Thread(target=work, daemon=True).start()

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

    def run_ai_agent(self) -> None:
        self._save()
        self._log("[*] AI 代理启动…")
        self.status.set("AI 运行中")

        def work():
            from verify_auto.ai_agent import run_strong_agent

            def progress(msg: str) -> None:
                self.after(0, lambda m=msg: self._log(m))

            return run_strong_agent(
                self.cfg,
                keyword_override=self.keyword.get().strip(),
                on_progress=progress,
                max_attempts=3,
            )

        def done(r):
            self._log(("[OK] " if r.ok else "[FAIL] ") + r.message)
            self.status.set(r.message)

        self._run_bg(work, done)

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
                areas.step1_prompt,
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
