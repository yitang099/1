import os
import time

import numpy as np
from PIL import Image

from .local_image_solver import solve_local_image_pick


def _save_debug(img_rgb, tag, debug_dir):
    if not debug_dir:
        return
    os.makedirs(debug_dir, exist_ok=True)
    path = os.path.join(debug_dir, f"{tag}_{int(time.time())}.png")
    Image.fromarray(img_rgb).save(path)


def solve_image_pick(img_rgb, cfg):
    if isinstance(cfg, dict) and "api" in cfg:
        local_cfg = cfg.get("local", {})
        debug_dir = cfg.get("api", {}).get("debug_dir", "debug")
    else:
        local_cfg = {}
        debug_dir = "debug"

    result, err = solve_local_image_pick(img_rgb, local_cfg)
    if err:
        _save_debug(img_rgb, "fail", debug_dir)
        return None, err

    _save_debug(img_rgb, "ok", debug_dir)
    return result, None
