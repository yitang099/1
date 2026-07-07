"""生成类人滑动轨迹。"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class DragTrack:
    offsets: list[int]
    total: int
    duration_ms: int


def generate_track(distance: int, *, duration_ms: int = 800) -> DragTrack:
    """生成带加速/减速/微抖动的横向位移序列。"""
    if distance <= 0:
        return DragTrack(offsets=[], total=0, duration_ms=duration_ms)

    offsets: list[int] = []
    current = 0
    mid = distance * random.uniform(0.75, 0.88)
    t = 0.15
    v = 0.0

    while current < distance:
        if current < mid:
            a = random.uniform(1.8, 3.2)
        else:
            a = -random.uniform(2.5, 4.5)
        v0 = v
        v = max(0.0, v0 + a * t)
        move = v0 * t + 0.5 * a * t * t
        move = int(round(max(1.0, move)))
        if current + move > distance:
            move = distance - current
        offsets.append(move)
        current += move

    # 轻微回拉更像真人
    if distance > 40 and random.random() < 0.7:
        back = random.randint(1, 3)
        offsets.append(-back)
        offsets.append(back)

    return DragTrack(offsets=offsets, total=sum(offsets), duration_ms=duration_ms)


def track_to_json_points(track: DragTrack, start_y: int = 0) -> list[dict[str, int]]:
    """部分站点需要 [{x,y,t}, ...] 格式。"""
    points: list[dict[str, int]] = []
    x = 0
    n = max(len(track.offsets), 1)
    step_ms = max(1, track.duration_ms // n)
    t = 0
    for dx in track.offsets:
        x += dx
        t += step_ms
        points.append({"x": x, "y": start_y + random.randint(-1, 1), "t": t})
    return points
