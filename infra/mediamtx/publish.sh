#!/bin/sh
# Publishes a looping "fake camera" stream into MediaMTX.
# MediaMTX sets MTX_PATH (e.g. cam1) and RTSP_PORT for runOnInit commands.
# Uses /videos/$MTX_PATH.mp4 when present, otherwise a synthetic test pattern.
set -eu

SRC="/videos/${MTX_PATH}.mp4"
TARGET="rtsp://localhost:${RTSP_PORT}/${MTX_PATH}"

# Re-encode to H.264 baseline-friendly settings so any input file works and
# browsers can play it over WebRTC/HLS. -re keeps real-time speed like a camera.
ENCODE="-an -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p -g 25 -bf 0"

if [ -f "$SRC" ]; then
  echo "[$MTX_PATH] publishing $SRC" >&2
  # shellcheck disable=SC2086
  exec ffmpeg -hide_banner -loglevel error -re -stream_loop -1 -i "$SRC" \
    $ENCODE -f rtsp -rtsp_transport tcp "$TARGET"
else
  echo "[$MTX_PATH] $SRC not found - publishing test pattern" >&2
  # shellcheck disable=SC2086
  exec ffmpeg -hide_banner -loglevel error -re \
    -f lavfi -i "testsrc2=size=1280x720:rate=25" \
    $ENCODE -f rtsp -rtsp_transport tcp "$TARGET"
fi
