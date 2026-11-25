# ANPR Platform

Real-time, multi-camera **Automatic Number Plate Recognition** for **Indian** and **UAE**
plates (per emirate), built like a city-scale deployment: an edge vision worker,
an event queue, a backend API, time-series storage, S3 image storage, alerts and a
live dashboard.

> Status: **Milestone 0 — foundation** (infrastructure, fake cameras, health checks, CI).

## Architecture

```
 Cameras (RTSP)  ── dev: data/videos/camN.mp4 replayed by MediaMTX
       │
       ▼
 Vision worker (native on Mac / GPU container in prod)
   YOLO11 vehicles → ByteTrack → zone → plate detector → region/emirate
   → plate OCR → format rules → multi-frame vote → one event per vehicle
       │
       ▼
 Redis Streams ──► FastAPI ──► PostgreSQL + TimescaleDB (readings, search)
                     │    └──► S3 storage (plate / vehicle images, auto-expiry)
                     ▼
              React dashboard · alert worker · Prometheus / Grafana
```

| Component | Technology |
|---|---|
| Detection / tracking | YOLO11, ByteTrack |
| Plate OCR | fast-plate-ocr (CCT), fine-tuned on Indian + UAE plates |
| Inference | ONNX Runtime — CoreML on Mac, TensorRT on NVIDIA |
| Video | MediaMTX (RTSP, HLS, WebRTC) |
| Event queue | Redis Streams |
| Backend | FastAPI |
| Database | PostgreSQL 16 + TimescaleDB + pg_trgm |
| Object storage | S3 API — SeaweedFS locally, any S3 (e.g. AWS) in production |
| Dashboard | React + TypeScript + Vite |
| Ops | Docker Compose, GitHub Actions, Prometheus, Grafana |

## Quick start

Requirements: Docker Desktop, Python 3.11+, make.

```bash
make install   # virtualenvs for api/ and vision/
make up        # creates .env with random passwords, starts the stack
make health    # postgres / redis / s3 readiness
make cameras   # connects to every camera, reports resolution and fps
```

Expected `make cameras` output:

```
camera   status resolution    fps  detail
cam1     OK     1280x720     25.0  rtsp://localhost:8554/cam1
...
```

Without video files each camera shows a test pattern. To use real footage, drop clips
into `data/videos/` as `cam1.mp4`, `cam2.mp4`, … and run `docker compose restart mediamtx`.
Preview a camera in the browser: <http://localhost:8888/cam1>.

### Services (all bound to 127.0.0.1)

| Service | Port | Notes |
|---|---|---|
| API | 8000 | `/health/live`, `/health/ready`, docs at `/docs` |
| PostgreSQL | 5433 | 5433 avoids clashing with a local Postgres |
| Redis | 6379 | password-protected, AOF persistence |
| S3 (SeaweedFS) | 8333 | bucket `anpr-images`, objects expire after `IMAGE_RETENTION_DAYS` |
| MediaMTX | 8554 / 8888 / 8889 | RTSP / HLS / WebRTC |

## Development

```bash
make test               # unit tests (api + vision)
make test-integration   # tests against the running stack
make lint               # ruff lint + format check
make fmt                # auto-fix
make logs s=mediamtx    # follow one service's logs
make down               # stop (keeps data)
make clean              # stop and DELETE all data volumes
```

## Repository layout

```
api/            FastAPI backend (health checks now; events, search, auth later)
vision/         vision worker (camera registry + checks now; ML pipeline from milestone 1)
config/         cameras.yaml — camera URLs, plate region hint, monitoring zone
infra/          MediaMTX, Postgres init, SeaweedFS start script
data/videos/    local test footage (git-ignored)
scripts/        helper scripts
docs/           milestone documents and development workflow
.github/        CI, pull request template
```

## Documentation

- [Milestones](docs/milestones/README.md): one document per milestone covering what was
  built, why, libraries, design decisions and verified results
- [Workflow](docs/workflow.md): one branch and one pull request per milestone

## Configuration

- Secrets live only in `.env` (git-ignored). `make env` generates it from `.env.example`.
- Camera URLs in `config/cameras.yaml` support `${VAR}` / `${VAR:-default}`, so camera
  credentials stay in `.env`.
- Monitoring zones are polygons in normalised 0..1 coordinates, independent of resolution.

## Roadmap

| # | Milestone |
|---|---|
| 0 | ✅ Foundation — stack, fake cameras, health checks, CI |
| 1 | Baseline pipeline — detection, tracking, zone, pretrained plate OCR |
| 2 | Data + training — Indian + UAE plate detector, region classifier, OCR fine-tune |
| 3 | Accuracy layer — region rules, OCR error correction, voting, evaluation set |
| 4 | Backend — event ingestion, storage, search, WebSocket, auth, audit log |
| 5 | Dashboard + alerts — React UI, live video, watchlists, Telegram alerts |
| 6 | Production hardening — ONNX/TensorRT, multi-camera load test, monitoring, HTTPS |
| 7 | Documentation + demo |

## Privacy

Number plates are personal data. Only process footage you are permitted to use. Images
expire automatically, data is retained for a configurable period, and access will be
role-based with an audit log (milestone 4). Design follows India's DPDP Act 2023 and the
UAE PDPL.
