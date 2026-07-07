"""第2步：只追踪【会动的球】，在动球里选最慢的。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from slider_solver.screen_match import Region, grab_region


@dataclass
class MotionTrack:
    track_id: int
    positions: list[tuple[int, int]] = field(default_factory=list)
    total_move: float = 0.0
    avg_area: float = 0.0

    def add(self, x: int, y: int, area: float) -> None:
        if self.positions:
            px, py = self.positions[-1]
            self.total_move += ((x - px) ** 2 + (y - py) ** 2) ** 0.5
        self.positions.append((x, y))
        n = len(self.positions)
        self.avg_area = (self.avg_area * (n - 1) + area) / n


@dataclass
class SlowestBallResult:
    ok: bool
    message: str
    click_x: int = 0
    click_y: int = 0
    movers: list[tuple[int, float]] = field(default_factory=list)
    stationary_count: int = 0


# 总位移低于此 = 背景装饰球（不动）
STATIONARY_MOVE_PX = 6.0
# 单帧位移差分面积范围（动球偏小）
MIN_AREA = 12
MAX_AREA = 2500


def _diff_centroids(prev: np.ndarray, curr: np.ndarray) -> list[tuple[int, int, float]]:
    """从连续两帧差分里找运动斑点中心。"""
    g0 = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
    g1 = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY)
    g0 = cv2.GaussianBlur(g0, (5, 5), 0)
    g1 = cv2.GaussianBlur(g1, (5, 5), 0)
    diff = cv2.absdiff(g0, g1)
    _, th = cv2.threshold(diff, 18, 255, cv2.THRESH_BINARY)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out: list[tuple[int, int, float]] = []
    for c in cnts:
        area = cv2.contourArea(c)
        if area < MIN_AREA or area > MAX_AREA:
            continue
        m = cv2.moments(c)
        if m["m00"] <= 0:
            continue
        cx = int(m["m10"] / m["m00"])
        cy = int(m["m01"] / m["m00"])
        out.append((cx, cy, area))
    return out


def _match_track(tracks: list[MotionTrack], x: int, y: int, max_dist: int = 55) -> MotionTrack | None:
    best: MotionTrack | None = None
    best_d = float(max_dist)
    for t in tracks:
        if not t.positions:
            continue
        lx, ly = t.positions[-1]
        d = ((x - lx) ** 2 + (y - ly) ** 2) ** 0.5
        if d < best_d:
            best_d = d
            best = t
    return best


def analyze_motion_tracks(frames: list[np.ndarray]) -> list[MotionTrack]:
    tracks: list[MotionTrack] = []
    next_id = 0
    for i in range(1, len(frames)):
        for cx, cy, area in _diff_centroids(frames[i - 1], frames[i]):
            t = _match_track(tracks, cx, cy)
            if t is None:
                t = MotionTrack(track_id=next_id)
                next_id += 1
                tracks.append(t)
            t.add(cx, cy, area)
    return tracks


def find_slowest_moving_ball(
    region: Region,
    *,
    frames: int = 15,
    interval_ms: int = 100,
    move_threshold: float = STATIONARY_MOVE_PX,
) -> SlowestBallResult:
    shots: list[np.ndarray] = []
    for i in range(frames):
        shots.append(grab_region(region))
        if i < frames - 1:
            time.sleep(interval_ms / 1000.0)

    tracks = analyze_motion_tracks(shots)
    movers = [t for t in tracks if t.total_move >= move_threshold and len(t.positions) >= 2]
    stationary = len(tracks) - len(movers)

    mover_info = [(t.track_id, t.total_move) for t in movers]

    if not movers:
        return SlowestBallResult(
            False,
            f"未检测到动球（追踪 {len(tracks)} 个，动 {len(movers)} 个）。加长采样或缩小框选区域",
            movers=mover_info,
            stationary_count=stationary,
        )

    if len(movers) == 1:
        slowest = movers[0]
    else:
        slowest = min(movers, key=lambda t: t.total_move)

    lx, ly = slowest.positions[-1]
    return SlowestBallResult(
        True,
        f"动球 {len(movers)} 个 / 静止 {stationary} 个 → 最慢 id={slowest.track_id} 移动={slowest.total_move:.1f}px",
        click_x=region.left + lx,
        click_y=region.top + ly,
        movers=[(f"#{i}", m) for i, m in mover_info],
        stationary_count=stationary,
    )


def save_debug_frames(frames: list[np.ndarray], out_dir: str | Path) -> None:
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(frames):
        cv2.imencode(".png", f)[1].tofile(str(p / f"ball_{i:02d}.png"))
