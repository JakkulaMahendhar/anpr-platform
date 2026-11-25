# Test videos

Put traffic clips here named after the camera they should play as:

```
data/videos/cam1.mp4   → rtsp://localhost:8554/cam1
data/videos/cam2.mp4   → rtsp://localhost:8554/cam2
data/videos/cam3.mp4   → rtsp://localhost:8554/cam3
```

MediaMTX replays each file in a loop as a fake live camera. If a file is missing,
that camera shows a test pattern instead. Restart MediaMTX after adding files:

```bash
docker compose restart mediamtx
```

Videos are git-ignored: never commit footage or plate images.
