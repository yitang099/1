# -*- mode: python ; coding: utf-8 -*-
import os

spec_dir = os.path.dirname(os.path.abspath(SPEC))
repo_root = os.path.dirname(spec_dir)

a = Analysis(
    [os.path.join(spec_dir, "launcher.py")],
    pathex=[repo_root],
    binaries=[],
    datas=[
        (os.path.join(spec_dir, "frida_hook.js"), "."),
        (os.path.join(spec_dir, "parse_qq_bind_uin.py"), "."),
    ],
    hiddenimports=[
        "qq_bind_client",
        "qq_bind_client.app",
        "qq_bind_client.adb_helper",
        "qq_bind_client.frida_runner",
        "qq_bind_client.config",
        "qq_bind_client.results",
        "qq_bind_client.parse_qq_bind_uin",
        "frida",
        "tkinter",
        "tkinter.ttk",
        "tkinter.scrolledtext",
        "tkinter.filedialog",
        "tkinter.messagebox",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="QQ查绑Hook",
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
