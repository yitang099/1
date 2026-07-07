"""第2步词库匹配：用收录的慢球/场景案例快速定位。"""
from __future__ import annotations

import cv2

from slider_solver.screen_match import Region, grab_region
from verify_auto.ball_slowest import find_circles_in_image
from verify_auto.library_cache import get_step2_cache, load_library_cache
from verify_auto.library_store import _similarity


def _crop_ball(bgr, cx: int, cy: int, radius: int | None = None):
    h, w = bgr.shape[:2]
    half = max(18, int((radius or 22) * 1.1))
    x1, y1 = max(0, cx - half), max(0, cy - half)
    x2, y2 = min(w, cx + half), min(h, cy + half)
    return bgr[y1:y2, x1:x2].copy()


def find_slow_ball_fast(region: Region, *, min_score: float = 0.55) -> tuple[int, int, float, str] | None:
    """词库极速找慢球。返回 (screen_x, screen_y, score, method)。"""
    load_library_cache()
    scene = grab_region(region)
    if scene is None or scene.size == 0:
        return None

    scenes, slow_refs = get_step2_cache()
    sh, sw = scene.shape[:2]
    best_scene_score = 0.0
    best_scene_hit: tuple[int, int, float] | None = None
    for ref_scene, meta in scenes:
        rh, rw = ref_scene.shape[:2]
        ref_scaled = cv2.resize(ref_scene, (sw, sh)) if (rh != sh or rw != sw) else ref_scene
        res = cv2.matchTemplate(scene, ref_scaled, cv2.TM_CCOEFF_NORMED)
        score = float(res.max()) if res.size else 0.0
        if score > best_scene_score and score >= 0.72:
            best_scene_score = score
            slow = meta.get("slowest") or {}
            cx = int(slow.get("cx", meta.get("slowest_x", 0)))
            cy = int(slow.get("cy", meta.get("slowest_y", 0)))
            if cx or cy:
                best_scene_hit = (region.left + cx, region.top + cy, score)

    if best_scene_hit:
        x, y, s = best_scene_hit
        return x, y, s, "场景匹配"

    circles = find_circles_in_image(scene)
    if slow_refs and circles:
        best_ball: tuple[int, int, float] | None = None
        for cx, cy, rad in circles:
            crop = _crop_ball(scene, cx, cy, rad)
            for _, ref_img in slow_refs:
                score = _similarity(crop, ref_img)
                if score >= min_score and (best_ball is None or score > best_ball[2]):
                    best_ball = (region.left + cx, region.top + cy, score)
        if best_ball:
            return best_ball[0], best_ball[1], best_ball[2], "慢球词库"

    return None
