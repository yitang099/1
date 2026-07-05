import ctypes
from ctypes import wintypes


def wegame_is_running():
    titles = []
    keywords = ("wegametq", "data提取", "提data", "wegame")

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _):
        if not ctypes.windll.user32.IsWindowVisible(hwnd):
            return True
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        if buff.value:
            titles.append(buff.value)
        return True

    ctypes.windll.user32.EnumWindows(callback, 0)
    for t in titles:
        low = t.lower()
        if any(k in low for k in keywords):
            return True
    return False
