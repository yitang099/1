import numpy as np

from .motion_solver import looks_like_motion


def _has_confirm_button(img_rgb, top_ratio=0.18, right_ratio=0.35):
    h, w = img_rgb.shape[:2]
    top = img_rgb[: max(8, int(h * top_ratio)), -max(20, int(w * right_ratio)) :]
    r, g, b = top[:, :, 0], top[:, :, 1], top[:, :, 2]
    blue_mask = (b > 140) & (g > 80) & (g < 200) & (r < 120)
    return int(blue_mask.sum()) > 25


def _has_image_grid(img_rgb):
    h, w = img_rgb.shape[:2]
    body = img_rgb[int(h * 0.22) :, :]
    gray = np.mean(body, axis=2).astype(np.uint8)
    edges = np.abs(gray[:, 1:].astype(int) - gray[:, :-1].astype(int))
    strong = (edges > 18).sum()
    color_var = float(np.std(body.astype(float)))
    return strong > 800 and color_var > 25


def detect_captcha(frame, motion_cfg=None):
    motion_cfg = motion_cfg or {}
    min_area = motion_cfg.get("min_area", 8)
    max_area = motion_cfg.get("max_area", 800)

    reasons = []
    if _has_confirm_button(frame):
        reasons.append("confirm")
    if looks_like_motion(frame, min_area, max_area):
        reasons.append("motion")
    if _has_image_grid(frame):
        reasons.append("image")

    if len(reasons) >= 2:
        return True, "+".join(reasons)
    if "confirm" in reasons and ("motion" in reasons or "image" in reasons):
        return True, "+".join(reasons)
    return False, ""
