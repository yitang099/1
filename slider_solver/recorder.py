"""监听鼠标，录制用户手动拖动。"""
from __future__ import annotations

import threading
from dataclasses import dataclass

from pynput import mouse

from slider_solver.records import crop_knob_patch, save_record
from slider_solver.screen_match import Region, grab_region


@dataclass
class RecordOutcome:
    ok: bool
    message: str
    record_id: str = ""


class DragRecorder:
    def __init__(
        self,
        region: Region,
        *,
        duration_ms: int = 900,
        on_finish,
    ) -> None:
        self.region = region
        self.duration_ms = duration_ms
        self.on_finish = on_finish
        self._press: tuple[int, int] | None = None
        self._before = None
        self._listener: mouse.Listener | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        self._listener = mouse.Listener(on_click=self._on_click)
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _in_region(self, x: int, y: int) -> bool:
        r = self.region
        return r.left <= x <= r.left + r.width and r.top <= y <= r.top + r.height

    def _on_click(self, x, y, button, pressed) -> None:
        if button != mouse.Button.left:
            return
        with self._lock:
            if pressed:
                if not self._in_region(x, y):
                    return
                self._press = (int(x), int(y))
                self._before = grab_region(self.region)
            else:
                if not self._press:
                    return
                x0, y0 = self._press
                self._press = None
                dx = int(x) - x0
                if abs(dx) < 15:
                    self.on_finish(RecordOutcome(False, "拖动距离太短，请横向拖过滑块"))
                    self.stop()
                    return
                if self._before is None:
                    self.on_finish(RecordOutcome(False, "未截到验证图"))
                    self.stop()
                    return
                rel_x = x0 - self.region.left
                rel_y = y0 - self.region.top
                knob = crop_knob_patch(self._before, rel_x, rel_y)
                rec = save_record(
                    region=self.region,
                    captcha_bgr=self._before,
                    knob_bgr=knob,
                    drag_distance=dx,
                    start_x=x0,
                    start_y=y0,
                    duration_ms=self.duration_ms,
                )
                self.on_finish(
                    RecordOutcome(
                        True,
                        f"已保存「{rec.name}」距离={dx}px 相似度库 id={rec.id}",
                        record_id=rec.id,
                    )
                )
                self.stop()
