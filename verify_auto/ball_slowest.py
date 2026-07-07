"""第2步：检测圆球并追踪位移，在动球里选最慢的。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from slider_solver.screen_match import Region, grab_region


@dataclass
class BallTrack:
    track_id: int
    positions: list[tuple[int, int]] = field(default_factory=list)
    radius: float = 0.0

    @property
    def total_move(self) -> float:
        if len(self.positions) < 2:
            return 0.0
        m = 0.0
        for i in range(1, len(self.positions)):
            x0, y0 = self.positions[i - 1]
            x1, y1 = self.positions[i]
            m += ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        return m


@dataclass
class SlowestBallResult:
    ok: bool
    message: str
    click_x: int = 0
    click_y: int = 0
    movers: list[tuple[int, float]] = field(default_factory=list)
    stationary_count: int = 0


STATIONARY_MOVE_PX = 4.0
MIN_MOVE_PX = 3.0
MIN_AREA = 12
MAX_AREA = 2500


def _find_circles(bgr: np.ndarray) -> list[tuple[int, int, int]]:
    """返回 (cx, cy, radius) 列表。"""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 5)
    h, w = gray.shape[:2]
    min_r = max(5, min(h, w) // 30)
    max_r = max(min_r + 4, min(h, w) // 6)
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(14, min_r * 2),
        param1=100,
        param2=16,
        minRadius=min_r,
        maxRadius=max_r,
    )
    out: list[tuple[int, int, int]] = []
    if circles is not None:
        for c in circles[0]:
            out.append((int(c[0]), int(c[1]), int(c[2])))
    contour_hits = _find_circles_contour(bgr, min_r, max_r)
    for hit in contour_hits:
        if not any(((hit[0] - x) ** 2 + (hit[1] - y) ** 2) ** 0.5 < 15 for x, y, _ in out):
            out.append(hit)
    return out


def _find_circles_contour(bgr: np.ndarray, min_r: int, max_r: int) -> list[tuple[int, int, int]]:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out: list[tuple[int, int, int]] = []
    for c in cnts:
        area = cv2.contourArea(c)
        if area < 80 or area > 12000:
            continue
        (fx, fy), fr = cv2.minEnclosingCircle(c)
        r = int(fr)
        if r < min_r or r > max_r:
            continue
        peri = cv2.arcLength(c, True)
        if peri <= 0:
            continue
        circularity = 4 * np.pi * area / (peri * peri)
        if circularity < 0.5:
            continue
        out.append((int(fx), int(fy), r))
    return out


def _match_track(tracks: list[BallTrack], x: int, y: int, *, max_dist: int = 42) -> BallTrack | None:
    best: BallTrack | None = None
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


def _track_circles(frames: list[np.ndarray]) -> list[BallTrack]:
    tracks: list[BallTrack] = []
    next_id = 0
    for img in frames:
        for cx, cy, r in _find_circles(img):
            t = _match_track(tracks, cx, cy)
            if t is None:
                t = BallTrack(track_id=next_id, radius=r)
                next_id += 1
                tracks.append(t)
            t.positions.append((cx, cy))
            t.radius = (t.radius + r) / 2 if t.radius else r
    return tracks


def _diff_centroids(prev: np.ndarray, curr: np.ndarray) -> list[tuple[int, int, float]]:
    g0 = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
    g1 = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY)
    g0 = cv2.GaussianBlur(g0, (5, 5), 0)
    g1 = cv2.GaussianBlur(g1, (5, 5), 0)
    diff = cv2.absdiff(g0, g1)
    _, th = cv2.threshold(diff, 16, 255, cv2.THRESH_BINARY)
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
        out.append((int(m["m10"] / m["m00"]), int(m["m01"] / m["m00"]), area))
    return out


def _track_diff(frames: list[np.ndarray]) -> list[BallTrack]:
    tracks: list[BallTrack] = []
    next_id = 0
    for i in range(1, len(frames)):
        for cx, cy, _ in _diff_centroids(frames[i - 1], frames[i]):
            t = _match_track(tracks, cx, cy, max_dist=55)
            if t is None:
                t = BallTrack(track_id=next_id)
                next_id += 1
                tracks.append(t)
            t.positions.append((cx, cy))
    return tracks


def _movers_from_tracks(tracks: list[BallTrack], *, min_obs: int = 1) -> list[BallTrack]:
    movers: list[BallTrack] = []
    for t in tracks:
        if len(t.positions) < min_obs:
            continue
        if t.total_move >= MIN_MOVE_PX:
            movers.append(t)
    return movers


def _pick_movers(circle_tracks: list[BallTrack], diff_tracks: list[BallTrack]) -> tuple[list[BallTrack], list[BallTrack]]:
    movers = _movers_from_tracks(circle_tracks, min_obs=2)
    tracks = circle_tracks
    if len(movers) < 1:
        dm = _movers_from_tracks(diff_tracks, min_obs=2)
        if len(dm) >= len(movers):
            movers = dm
            tracks = diff_tracks
    if len(movers) < 1:
        movers = _movers_from_tracks(circle_tracks, min_obs=1)
        tracks = circle_tracks
    if len(movers) < 1:
        movers = _movers_from_tracks(diff_tracks, min_obs=1)
        tracks = diff_tracks
    return movers, tracks


def _rank_movers(movers: list[BallTrack]) -> list[BallTrack]:
    return sorted(movers, key=lambda t: t.total_move)


def _result_from_track(region: Region, track: BallTrack, movers: list[BallTrack], total: int) -> SlowestBallResult:
    lx, ly = track.positions[-1]
    stationary = max(0, total - len(movers))
    mover_info = [(t.track_id, t.total_move) for t in _rank_movers(movers)]
    return SlowestBallResult(
        True,
        f"动球 {len(movers)} 个 / 候选 {total} 个 → 最慢 id={track.track_id} 移动={track.total_move:.1f}px",
        click_x=region.left + lx,
        click_y=region.top + ly,
        movers=[(f"#{i}", m) for i, m in mover_info],
        stationary_count=stationary,
    )


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

    circle_tracks = _track_circles(shots)
    diff_tracks = _track_diff(shots)
    movers, tracks = _pick_movers(circle_tracks, diff_tracks)

    if not movers:
        return SlowestBallResult(
            False,
            f"未检测到动球（圆 {len(circle_tracks)} / 差分 {len(diff_tracks)}）。球区请框在网格位置",
            stationary_count=len(circle_tracks),
        )

    ranked = _rank_movers(movers)
    return _result_from_track(region, ranked[0], movers, len(circle_tracks))


def find_slowest_candidates(
    region: Region,
    *,
    frames: int = 15,
    interval_ms: int = 100,
    top_n: int = 3,
) -> list[SlowestBallResult]:
    """返回最慢的几个候选点击点（用于点错时重试）。"""
    shots: list[np.ndarray] = []
    for i in range(frames):
        shots.append(grab_region(region))
        if i < frames - 1:
            time.sleep(interval_ms / 1000.0)

    tracks = _track_circles(shots)
    diff_tracks = _track_diff(shots)
    movers, tracks = _pick_movers(tracks, diff_tracks)

    if not movers:
        return []

    ranked = _rank_movers(movers)[:top_n]
    return [_result_from_track(region, t, movers, len(tracks)) for t in ranked]


def find_slowest_in_areas(
    areas: list[Region],
    *,
    frames: int = 15,
    interval_ms: int = 100,
    top_n: int = 3,
) -> tuple[list[SlowestBallResult], Region | None]:
    """依次尝试多个区域（球区、网格区），返回候选和命中的区域。"""
    for region in areas:
        cands = find_slowest_candidates(region, frames=frames, interval_ms=interval_ms, top_n=top_n)
        if cands:
            return cands, region
    return [], None


def save_debug_frames(frames: list[np.ndarray], out_dir: str | Path) -> None:
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(frames):
        cv2.imencode(".png", f)[1].tofile(str(p / f"ball_{i:02d}.png"))
