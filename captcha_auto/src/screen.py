import time

import mss
import numpy as np
from PIL import Image


def grab_region(region):
    with mss.mss() as sct:
        shot = sct.grab(
            {
                "left": int(region["left"]),
                "top": int(region["top"]),
                "width": int(region["width"]),
                "height": int(region["height"]),
            }
        )
        # mss 各版本: bgra / raw，无 bgr 属性
        pixels = getattr(shot, "bgra", None) or getattr(shot, "raw", None)
        if pixels is None:
            pixels = np.asarray(shot)[:, :, :3].tobytes()
            img = Image.frombytes("RGB", shot.size, pixels, "raw", "RGB")
        else:
            img = Image.frombytes("RGB", shot.size, pixels, "raw", "BGRX")
        return np.array(img)


def grab_frames(region, count, interval_ms):
    frames = []
    for _ in range(count):
        frames.append(grab_region(region))
        time.sleep(interval_ms / 1000.0)
    return frames


def region_to_screen(region, x, y):
    return int(region["left"] + x), int(region["top"] + y)
