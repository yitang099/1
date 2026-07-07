"""多帧截图追踪小球，找出移动最慢的一个。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from slider_solver.screen_match import Region, grab_region


@dataclass
class BallTrack:
    ball_id: int
    color_name: str
    positions: list[tuple[int, int]] = field(default_factory=list)
    total_move: float = 0.0

    @property
    def avg_speed(self) -> float:
        if len(self.positions) < 2:
            return 0.0
        dist = 0.0
        for i in range(1, len(self.positions)):
            x0, y0 = self.positions[i - 1]
            x1, y1 = self.positions[i]
            dist += ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        return dist / (len(self.positions) - 1)


# 常见球色 HSV 范围（可按你软件微调）
COLOR_RANGES: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "red1": ((0, 80, 80), (10, 255, 255)),
    "red2": ((160, 80, 80), (180, 255, 255)),
    "orange": ((10, 80, 80), (25, 255, 255)),
    "yellow": ((25, 80, 80), (35, 255, 255)),
    "green": ((35, 60, 60), (85, 255, 255)),
    "cyan": ((85, 60, 60), (100, 255, 255)),
    "blue": ((100, 80, 80), (130, 255, 255)),
    "purple": ((130, 60, 60), (160, 255, 255)),
}


@dataclass
class SlowestBallResult:
    ok: bool
    message: str
    click_x: int = 0
    click_y: int = 0
    ball_id: int = -1
    color: str = ""
    speeds: list[tuple[str, float]] = field(default_factory=list)


def _mask_color(hsv: np.ndarray, low: tuple[int, int, int], high: tuple[int, int, int]) -> np.ndarray:
    return cv2.inRange(hsv, np.array(low), np.array(high))


def _find_blobs(mask: np.ndarray, min_area: int = 80) -> list[tuple[int, int, int]]:
    """返回 (cx, cy, area)。"""
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out: list[tuple[int, int, int]] = []
    for c in cnts:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        m = cv2.moments(c)
        if m["m00"] <= 0:
            continue
        cx = int(m["m10"] / m["m00"])
        cy = int(m["m01"] / m["m00"])
        out.append((cx, cy, int(area)))
    return out


def _match_track(tracks: list[BallTrack], x: int, y: int, max_dist: int = 40) -> BallTrack | None:
    best: BallTrack | None = None
    best_d = max_dist
    for t in tracks:
        if not t.positions:
            continue
        lx, ly = t.positions[-1]
        d = ((x - lx) ** 2 + (y - ly) ** 2) ** 0.5
        if d < best_d:
            best_d = d
            best = t
    return best


def analyze_frames(frames: list[np.ndarray]) -> list[BallTrack]:
    tracks: list[BallTrack] = []
    next_id = 0

    for frame in frames:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        for color_name, (low, high) in COLOR_RANGES.items():
            mask = _mask_color(hsv, low, high)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            for cx, cy, _ in _find_blobs(mask):
                t = _match_track(tracks, cx, cy)
                if t is None:
                    t = BallTrack(ball_id=next_id, color_name=color_name)
                    next_id += 1
                    tracks.append(t)
                t.positions.append((cx, cy))

    for t in tracks:
        if len(t.positions) >= 2:
            move = 0.0
            for i in range(1, len(t.positions)):
                x0, y0 = t.positions[i - 1]
                x1, y1 = t.positions[i]
                move += ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
            t.total_move = move
    return tracks


def find_slowest_ball(
    region: Region,
    *,
    frames: int = 12,
    interval_ms: int = 120,
) -> SlowestBallResult:
    import time

    shots: list[np.ndarray] = []
    for i in range(frames):
        shots.append(grab_region(region))
        if i < frames - 1:
            time.sleep(interval_ms / 1000.0)

    tracks = analyze_frames(shots)
    valid = [t for t in tracks if len(t.positions) >= 3]
    if len(valid) < 2:
        return SlowestBallResult(False, f"只追踪到 {len(valid)} 个球，请框准球区域或加长采样")

    speeds = [(f"#{t.ball_id}({t.color_name})", t.total_move) for t in valid]
    slowest = min(valid, key=lambda t: t.total_move)
    lx, ly = slowest.positions[-1]
    click_x = region.left + lx
    click_y = region.top + ly
    return SlowestBallResult(
        True,
        f"最慢球 id={slowest.ball_id} 颜色={slowest.color_name} 移动={slowest.total_move:.1f}px",
        click_x=click_x,
        click_y=click_y,
        ball_id=slowest.ball_id,
        color=slowest.color_name,
        speeds=speeds,
    )


def save_debug_frames(frames: list[np.ndarray], out_dir: str | Path) -> None:
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(frames):
        cv2.imencode(".png", f)[1].tofile(str(p / f"frame_{i:02d}.png"))
