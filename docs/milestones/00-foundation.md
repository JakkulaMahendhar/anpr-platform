# Milestone 0: Foundation

| | |
|---|---|
| **Branch** | `milestone/0-foundation` |
| **Status** | In review |
| **Goal** | A working, tested base for the rest of the system, before any ML code exists |
| **Result** | 5 services running and healthy, 3 fake cameras at 25 fps, 22 unit tests + 1 integration test passing, CI configured |

---

## 1. Why start with a foundation milestone?

The ML pipeline (Milestone 1+) needs somewhere to send its results, cameras to read
from, and a way to prove it works. Building these first means:

- **Every later milestone plugs into something real**, instead of a CSV file that gets
  replaced later.
- **Problems surface early.** This milestone already found two that would have blocked
  later work: MinIO images are no longer publicly available, and port 5432 was taken by a
  local Postgres.
- **We can test without real cameras.** Fake cameras let anyone run the system with no
  hardware.

---

## 2. What was built

```
                     ┌──────────────── Docker Compose ──────────────────┐
 data/videos/*.mp4 ──► MediaMTX  ── RTSP :8554 ──┐                      │
 (or test pattern)   │ (fake cameras)            │                      │
                     │                           │                      │
                     │  PostgreSQL+Timescale :5433   Redis :6379        │
                     │  SeaweedFS S3 :8333           FastAPI :8000      │
                     └───────────────────────────┼──────────────────────┘
                                                 │
 vision/ (runs natively on the Mac) ─────────────┘
   anpr.tools.check_cameras → reads every camera, reports resolution + fps
```

| Area | What exists | Main files |
|---|---|---|
| Infrastructure | 5 services, healthchecks, persistent volumes, ports bound to localhost only | `compose.yaml` |
| Fake cameras | MediaMTX replays `data/videos/camN.mp4` in a loop, or a test pattern if the file is missing | `infra/mediamtx/` |
| Database | PostgreSQL 16 with TimescaleDB and pg_trgm enabled on first start | `infra/postgres/init/` |
| Image storage | S3-compatible storage, bucket created automatically, images auto-deleted after N days | `infra/seaweedfs/`, `api/app/storage.py` |
| API | `/health/live` and `/health/ready` (checks Postgres, Redis and S3 in parallel) | `api/app/` |
| Camera registry | `config/cameras.yaml`, validated: URLs, region hint, monitoring zone | `vision/anpr/config.py` |
| Camera check tool | Connects to every camera and measures real fps | `vision/anpr/tools/check_cameras.py` |
| Secrets | `.env` generated with random passwords, git-ignored | `scripts/make_env.py` |
| Developer tooling | `make` commands, ruff linting, pytest, GitHub Actions CI | `Makefile`, `ruff.toml`, `.github/` |

---

## 3. Libraries and services

### Infrastructure (Docker images)

| Service | Image | Role | Why this choice |
|---|---|---|---|
| PostgreSQL + TimescaleDB | `timescale/timescaledb:2.17.2-pg16` | Main database | Plate readings are time-series data. TimescaleDB adds automatic partitioning by time, fast time-range queries and retention policies on top of normal Postgres, so we keep SQL, joins and transactions. |
| pg_trgm (extension) | built into Postgres | Fuzzy plate search | Finds `TS09AB1234` when someone searches `TS09AB` or the OCR read `TS09A81234`. Avoids running a separate Elasticsearch. |
| Redis | `redis:7.4-alpine` | Event queue (from Milestone 4) | Redis Streams give durable queues with consumer groups and acknowledgements, so no plate event is lost if the API restarts. Much simpler to run than Kafka at this scale. AOF persistence and a password are on. |
| SeaweedFS | `chrislusf/seaweedfs:3.97` | Image storage (S3 API) | Stores plate and vehicle crops. Apache-2.0 licensed, speaks the standard S3 API, and supports lifecycle rules (auto-delete). |
| MediaMTX | `bluenviron/mediamtx:1.9.3-ffmpeg` | Video server | Industry-standard open-source RTSP server. Replays video files as fake cameras now, and will stream live video to the browser over WebRTC in Milestone 5. The `-ffmpeg` variant includes ffmpeg, so nothing needs installing on the Mac. |

### API (`api/`, Python 3.11)

| Library | Version | Why |
|---|---|---|
| FastAPI | 0.165 | Async, automatic OpenAPI docs at `/docs`, type-checked request/response models. The standard for Python ML backends. |
| Uvicorn | 0.54 | Production ASGI server for FastAPI. |
| pydantic-settings | 2.16 | Loads configuration from environment variables / `.env` with type validation. Passwords are `SecretStr`, so they never appear in logs. |
| asyncpg | 0.32 | Fastest async PostgreSQL driver. |
| redis (redis-py) | 5.3 | Official Redis client with asyncio support. |
| boto3 | 1.44 | Official AWS S3 client. Works with SeaweedFS now and with real AWS S3 in production, by changing only the endpoint. |

### Vision worker (`vision/`)

| Library | Version | Why |
|---|---|---|
| opencv-python-headless | 4.14 | Reads RTSP streams and video frames. The headless build has no GUI dependencies, which suits servers and containers. |
| NumPy | 2.4 | Frame arrays. |
| pydantic | 2.14 | Validates `cameras.yaml`, so a typo fails at start-up with a clear message instead of mid-stream. |
| PyYAML | 6.0 | Reads the camera config. |

### Development

| Tool | Why |
|---|---|
| pytest (+ pytest-asyncio, httpx) | Unit tests, async tests and API tests without starting a server. |
| ruff | One fast tool for linting and formatting (replaces flake8, isort and black). |
| GitHub Actions | Runs lint, tests, compose validation and the API image build on every push and PR. |
| make | Short, memorable commands (`make up`, `make test`) that document the workflow. |

---

## 4. Key design decisions

| Decision | Reason |
|---|---|
| **The vision worker runs outside Docker on the Mac** | Docker on macOS cannot use the Apple GPU. Running natively allows CoreML/MPS acceleration. In production (Linux + NVIDIA) it runs in a GPU container. |
| **SeaweedFS instead of MinIO** | MinIO's Docker images are no longer publicly downloadable (verified: `pull access denied`). SeaweedFS was tested before switching: S3 operations, lifecycle rules and rejection of wrong credentials all work. |
| **API uses the generic S3 client (boto3), not a vendor SDK** | Storage can be swapped (SeaweedFS → AWS S3 → anything S3-compatible) through configuration alone. |
| **All ports bound to 127.0.0.1** | Nothing is reachable from your network by default. Production exposes only the HTTPS reverse proxy (Milestone 6). |
| **Postgres on host port 5433** | Port 5432 is used by a local Postgres on the development Mac. Inside Docker it is still 5432. |
| **Random passwords generated into `.env`** | No default or shared passwords. `.env` is git-ignored, `.env.example` documents the variables. |
| **Camera URLs support `${VAR}` expansion** | Real camera credentials stay in `.env`, never in `cameras.yaml` or git. A missing variable is an error, not a silently broken URL. |
| **Monitoring zones use 0..1 coordinates** | The same zone works whether a camera sends 720p or 4K. |
| **Liveness vs readiness endpoints** | `/health/live` tells Docker or Kubernetes the process is alive. `/health/ready` checks all dependencies and returns 503 if one is down, so traffic is routed only to working instances. This is the standard pattern for orchestrated services. |
| **Health checks run in parallel with a timeout** | One slow dependency can't make the whole health check hang. |
| **Images auto-expire (default 30 days)** | Plate images are personal data. Automatic deletion supports India's DPDP Act and the UAE PDPL, and keeps storage bounded. |
| **Fake cameras re-encode to H.264** | Any MP4 works as input, and browsers can play the stream over WebRTC/HLS later. |
| **Camera check discards warm-up frames** | A newly opened stream delivers buffered frames faster than real time. The first version reported 35 fps for a 25 fps stream; discarding warm-up frames gives the true rate. |

---

## 5. How to run and verify

```bash
make install            # create api/.venv and vision/.venv
make up                 # create .env, start all services, wait until healthy
make health             # expect "ok": true for postgres, redis, s3
make cameras            # expect 3 cameras: OK, 1280x720, 25.0 fps
make test               # unit tests
make test-integration   # test against the running stack
make lint
```

Open <http://localhost:8888/cam1> to watch a fake camera in the browser and
<http://localhost:8000/docs> for the API docs.

### Verified results

| Check | Result |
|---|---|
| `docker compose ps` | postgres, redis, s3, mediamtx, api all up (healthy) |
| `make health` | postgres ✓, redis ✓, s3 ✓ |
| `make cameras` | cam1–cam3 OK, 1280x720, 25.0 fps |
| MP4 as a camera | 960x540 test clip published and read correctly |
| Postgres extensions | timescaledb 2.17.2, pg_trgm 1.6 |
| Unit tests | api: 6 passed, vision: 16 passed |
| Integration test | 1 passed (real Postgres, Redis, S3) |
| Lint | ruff: all checks passed |

---

## 6. Tests

| Test file | What it covers |
|---|---|
| `api/tests/test_health.py` | Readiness reports each dependency; 503 when one is down; a hanging dependency times out; retention rule; integration test against the real stack |
| `vision/tests/test_config.py` | The repo's `cameras.yaml` is valid; env-variable expansion and missing-variable errors; invalid zone, id, region and URL rejected; duplicate ids rejected; zone to pixel conversion |
| `vision/tests/test_check_cameras.py` | fps measurement, warm-up discarding, no frames, stream stopping early (uses a fake capture, so no camera is needed) |

---

## 7. Reviewer guide

Suggested reading order for the PR:

1. `README.md`: overview and commands
2. `compose.yaml`: all services and how they connect
3. `config/cameras.yaml` → `vision/anpr/config.py`: camera registry and validation
4. `api/app/health.py`, `api/app/storage.py`, `api/app/main.py`: API
5. `infra/`: MediaMTX, Postgres init, SeaweedFS start script
6. Tests, then `Makefile` and `.github/workflows/ci.yml`

---

## 8. Known limitations (deliberately deferred)

| Item | Planned in |
|---|---|
| Database tables and migrations (Alembic) | Milestone 4 |
| Redis is running but not used yet | Milestone 4 (event queue) |
| API has no authentication yet | Milestone 4 |
| API and S3 use admin-level storage credentials | Milestone 6 (scoped credentials) |
| No HTTPS, metrics or Grafana yet | Milestone 6 |
| The readiness endpoint shows error details; it should be restricted once auth exists | Milestone 4 |
| CI has not run on GitHub yet (repository not pushed) | First push |

---

## 9. Next: Milestone 1, baseline pipeline

YOLO11 vehicle detection, ByteTrack tracking, monitoring zone, pretrained plate
detector + fast-plate-ocr, printing one plate reading per vehicle, plus the first
accuracy numbers on Indian and UAE footage.
