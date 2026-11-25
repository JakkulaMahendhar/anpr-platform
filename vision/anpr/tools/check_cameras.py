"""Connect to every enabled camera and report resolution and real frame rate.

    python -m anpr.tools.check_cameras [--config PATH] [--frames 50]

Exit code is non-zero if any camera fails, so this doubles as a smoke test.
"""

import argparse
import os
import sys
import time
from dataclasses import dataclass
from typing import Protocol

# Force RTSP over TCP: no packet loss / smeared frames on lossy networks.
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

import cv2

from anpr.config import Camera, load_cameras


class Capture(Protocol):
    def read(self) -> tuple[bool, object]: ...
    def release(self) -> None: ...


@dataclass
class StreamStats:
    ok: bool
    frames: int = 0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    error: str = ""


def measure(cap: Capture, frames: int, warmup: int = 0, clock=time.perf_counter) -> StreamStats:
    """Read `frames` frames and measure the delivered frame rate.

    The first `warmup` frames are discarded untimed: a freshly opened stream delivers
    its buffered backlog faster than real time, which would overstate the fps.
    """
    ok, frame = cap.read()
    if not ok or frame is None:
        return StreamStats(ok=False, error="no frames received")
    height, width = frame.shape[:2]
    for _ in range(warmup):
        if not cap.read()[0]:
            return StreamStats(False, 0, width, height, error="stream stopped during warm-up")
    start, count = clock(), 0
    while count < frames:
        ok, frame = cap.read()
        if not ok:
            error = f"stream stopped after {count} frames"
            return StreamStats(False, count, width, height, error=error)
        count += 1
    elapsed = clock() - start
    fps = count / elapsed if elapsed > 0 else 0.0
    return StreamStats(True, count, width, height, round(fps, 1))


def open_capture(camera: Camera, timeout_ms: int) -> cv2.VideoCapture:
    params = [
        cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms,
        cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms,
    ]  # fmt: skip
    return cv2.VideoCapture(camera.url, cv2.CAP_FFMPEG, params)


def check(camera: Camera, frames: int, warmup: int, timeout_ms: int) -> StreamStats:
    cap = open_capture(camera, timeout_ms)
    try:
        if not cap.isOpened():
            return StreamStats(ok=False, error="could not open stream")
        return measure(cap, frames, warmup)
    finally:
        cap.release()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", help="cameras.yaml path (default: config/cameras.yaml)")
    parser.add_argument("--frames", type=int, default=50, help="frames to time per camera")
    parser.add_argument("--warmup", type=int, default=50, help="frames to discard first")
    parser.add_argument("--timeout-ms", type=int, default=5000)
    args = parser.parse_args(argv)

    registry = load_cameras(args.config)
    print(f"{'camera':<8} {'status':<6} {'resolution':<11} {'fps':>5}  detail")
    failures = 0
    for cam in registry.enabled:
        s = check(cam, args.frames, args.warmup, args.timeout_ms)
        failures += not s.ok
        res = f"{s.width}x{s.height}" if s.width else "-"
        status = "OK" if s.ok else "FAIL"
        print(f"{cam.id:<8} {status:<6} {res:<11} {s.fps:>5}  {s.error or cam.url}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
