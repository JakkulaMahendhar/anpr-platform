import numpy as np

from anpr.tools.check_cameras import measure


class FakeCapture:
    def __init__(self, frames: int, shape=(720, 1280, 3)):
        self.remaining = frames
        self.frame = np.zeros(shape, dtype=np.uint8)

    def read(self):
        if self.remaining <= 0:
            return False, None
        self.remaining -= 1
        return True, self.frame

    def release(self):
        pass


def fake_clock(step: float):
    t = [0.0]

    def clock():
        t[0] += step
        return t[0]

    return clock


def test_measure_reports_resolution_and_fps():
    # 1 probe frame + 10 measured frames; clock is called twice -> 1 tick of 0.4s
    stats = measure(FakeCapture(11), frames=10, clock=fake_clock(0.4))
    assert stats.ok
    assert (stats.width, stats.height) == (1280, 720)
    assert stats.fps == 25.0


def test_measure_discards_warmup_frames():
    cap = FakeCapture(1 + 5 + 10)
    stats = measure(cap, frames=10, warmup=5, clock=fake_clock(1.0))
    assert stats.ok and stats.frames == 10
    assert cap.remaining == 0


def test_measure_stream_stops_during_warmup():
    stats = measure(FakeCapture(3), frames=10, warmup=5)
    assert not stats.ok
    assert "warm-up" in stats.error


def test_measure_no_frames():
    stats = measure(FakeCapture(0), frames=10)
    assert not stats.ok
    assert stats.error == "no frames received"


def test_measure_stream_stops_early():
    stats = measure(FakeCapture(5), frames=10)
    assert not stats.ok
    assert "after 4 frames" in stats.error
