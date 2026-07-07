# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

spec_dir = os.path.dirname(os.path.abspath(SPEC))
repo_root = os.path.dirname(spec_dir)

ocr_datas, ocr_binaries, ocr_hidden = collect_all("rapidocr_onnxruntime")
ort_datas, ort_binaries, ort_hidden = collect_all("onnxruntime")

hidden = (
    collect_submodules("verify_auto")
    + collect_submodules("slider_solver")
    + [
        "verify_auto",
        "verify_auto.app",
        "verify_auto.pipeline",
        "verify_auto.config",
        "verify_auto.click_util",
        "verify_auto.region_resolve",
        "verify_auto.window_locate",
        "verify_auto.layout_profile",
        "verify_auto.ocr_util",
        "verify_auto.selection_marker",
        "verify_auto.learn",
        "verify_auto.library_store",
        "verify_auto.step1_library",
        "verify_auto.step1_pick",
        "verify_auto.ball_slowest",
        "verify_auto.screen_detect",
        "slider_solver",
        "slider_solver.screen_match",
        "cv2",
        "numpy",
        "PIL",
        "mss",
        "pyautogui",
        "pynput",
        "pynput.mouse",
        "pynput.keyboard",
        "onnxruntime",
        "rapidocr_onnxruntime",
        "tkinter",
        "tkinter.ttk",
        "tkinter.scrolledtext",
        "tkinter.messagebox",
    ]
    + ocr_hidden
    + ort_hidden
)

a = Analysis(
    [os.path.join(spec_dir, "launcher.py")],
    pathex=[repo_root],
    binaries=ocr_binaries + ort_binaries,
    datas=ocr_datas + ort_datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["torch", "transformers", "easyocr", "matplotlib", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="两步验证助手",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
