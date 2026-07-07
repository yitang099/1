"""点击：优先后台消息（不移动鼠标），失败则点完恢复光标位置。"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass


@dataclass
class ClickResult:
    ok: bool
    method: str
    message: str = ""


def click_screen(x: int, y: int, *, background: bool = True) -> ClickResult:
    x, y = int(x), int(y)
    if background and sys.platform == "win32":
        r = _click_win_message(x, y)
        if r.ok:
            return r
    return _click_pyautogui_restore(x, y)


def _click_win_message(x: int, y: int) -> ClickResult:
    """Windows: PostMessage 点击，系统鼠标不动。"""
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        WM_MOUSEMOVE = 0x0200
        WM_LBUTTONDOWN = 0x0201
        WM_LBUTTONUP = 0x0202
        MK_LBUTTON = 0x0001

        pt = POINT(x, y)
        hwnd = user32.WindowFromPoint(pt)
        if not hwnd:
            return ClickResult(False, "win_message", "该坐标下没有窗口")

        chain: list[int] = []
        cur = hwnd
        while cur:
            chain.append(cur)
            cur = user32.GetParent(cur)

        for h in chain:
            cpt = POINT(x, y)
            if not user32.ScreenToClient(h, ctypes.byref(cpt)):
                continue
            lp = (cpt.y & 0xFFFF) << 16 | (cpt.x & 0xFFFF)
            user32.PostMessageW(h, WM_MOUSEMOVE, 0, lp)
            user32.PostMessageW(h, WM_LBUTTONDOWN, MK_LBUTTON, lp)
            time.sleep(0.02)
            user32.PostMessageW(h, WM_LBUTTONUP, 0, lp)
            return ClickResult(True, "win_message", f"后台点击 hwnd={h}")

        return ClickResult(False, "win_message", "消息投递失败")
    except Exception as exc:
        return ClickResult(False, "win_message", str(exc))


def _click_pyautogui_restore(x: int, y: int) -> ClickResult:
    """物理点击后立即把鼠标移回原位（非 Windows 或后台失败时）。"""
    import pyautogui

    pos = pyautogui.position()
    pyautogui.click(x, y)
    pyautogui.moveTo(pos.x, pos.y, duration=0)
    return ClickResult(True, "pyautogui_restore", "已点击并恢复鼠标位置")
