import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status

from . import health, storage
from .config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("anpr.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await storage.ensure_bucket(get_settings())
    except Exception:
        # Start anyway; /health/ready reports the problem and the orchestrator decides.
        log.exception("could not prepare object storage bucket")
    yield


app = FastAPI(title="ANPR Platform API", version="0.1.0", lifespan=lifespan)


@app.get("/health/live", tags=["health"])
async def live() -> dict[str, str]:
    """Process is up. Used by Docker to restart a hung container."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def ready(response: Response) -> dict:
    """All dependencies reachable. Returns 503 if any is not."""
    result = await health.run_checks(get_settings())
    if not result["ok"]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
