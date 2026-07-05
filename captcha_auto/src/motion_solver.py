import cv2
import numpy as np


COLOR_RANGES = [
    ("red1", (0, 120, 120), (10, 255, 255)),
    ("red2", (170, 120, 120), (180, 255, 255)),
    ("green", (35, 80, 80), (85, 255, 255)),
    ("blue", (95, 80, 80), (130, 255, 255)),
    ("purple", (130, 60, 60), (165, 255, 255)),
    ("yellow", (20, 80, 80), (35, 255, 255)),
]


def _find_dots(frame_bgr, min_area, max_area):
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_RGB2HSV)
    dots = []
    for name, low, high in COLOR_RANGES:
        mask = cv2.inRange(hsv, np.array(low), np.array(high))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area or area > max_area:
                continue
            m = cv2.moments(c)
            if m["m00"] == 0:
                continue
            cx = int(m["m10"] / m["m00"])
            cy = int(m["m01"] / m["m00"])
            dots.append({"name": name, "x": cx, "y": cy, "area": area})
    return dots


def _cluster_tracks(all_frames_dots):
    tracks = []
    for dots in all_frames_dots:
        used = set()
        for d in dots:
            best_i = -1
            best_dist = 45
            for i, tr in enumerate(tracks):
                if tr["name"] != d["name"]:
                    continue
                lx, ly = tr["points"][-1]
                dist = abs(lx - d["x"]) + abs(ly - d["y"])
                if dist < best_dist:
                    best_dist = dist
                    best_i = i
            if best_i >= 0:
                tracks[best_i]["points"].append((d["x"], d["y"]))
                used.add(best_i)
            else:
                tracks.append({"name": d["name"], "points": [(d["x"], d["y"])]})
    return [t for t in tracks if len(t["points"]) >= 3]


def _track_distance(points):
    total = 0.0
    for i in range(1, len(points)):
        x1, y1 = points[i - 1]
        x2, y2 = points[i]
        total += ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    return total


def solve_motion(frames, min_area=8, max_area=800):
    all_dots = [_find_dots(f, min_area, max_area) for f in frames]
    if max(len(x) for x in all_dots) < 3:
        return None, "未检测到足够彩色圆点"

    tracks = _cluster_tracks(all_dots)
    if len(tracks) < 2:
        return None, "运动轨迹不足，请确保验证码完全在框选区域内"

    scored = []
    for tr in tracks:
        dist = _track_distance(tr["points"])
        last = tr["points"][-1]
        scored.append((dist, last[0], last[1], tr["name"]))

    scored.sort(key=lambda x: x[0])
    dist, x, y, name = scored[0]
    return {"x": x, "y": y, "type": "motion", "detail": f"最慢元素 {name}, 位移={dist:.1f}px"}, None


def looks_like_motion(frame, min_area=8, max_area=800):
    dots = _find_dots(frame, min_area, max_area)
    names = {d["name"] for d in dots}
    return len(dots) >= 4 and len(names) >= 3
