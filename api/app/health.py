"""Dependency health checks used by the readiness endpoint."""

import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import asyncpg
import redis.asyncio as aioredis

from . import storage
from .config import Settings

CheckFn = Callable[[Settings], Awaitable[None]]

REQUIRED_PG_EXTENSIONS = {"timescaledb", "pg_trgm"}


async def check_postgres(settings: Settings) -> None:
    conn = await asyncpg.connect(settings.postgres_dsn, timeout=3)
    try:
        rows = await conn.fetch("SELECT extname FROM pg_extension")
    finally:
        await conn.close()
    missing = REQUIRED_PG_EXTENSIONS - {r["extname"] for r in rows}
    if missing:
        raise RuntimeError(f"missing extensions: {sorted(missing)}")


async def check_redis(settings: Settings) -> None:
    client = aioredis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password.get_secret_value(),
        socket_connect_timeout=3,
    )
    try:
        await client.ping()
    finally:
        await client.aclose()


async def check_s3(settings: Settings) -> None:
    client = storage.make_client(settings)
    exists = await asyncio.to_thread(storage.bucket_exists, client, settings.s3_bucket)
    if not exists:
        raise RuntimeError(f"bucket {settings.s3_bucket!r} does not exist")


DEFAULT_CHECKS: Mapping[str, CheckFn] = {
    "postgres": check_postgres,
    "redis": check_redis,
    "s3": check_s3,
}


async def run_checks(
    settings: Settings,
    checks: Mapping[str, CheckFn] | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Run all checks concurrently; one slow or failing dependency never blocks the others."""
    checks = DEFAULT_CHECKS if checks is None else checks

    async def run_one(name: str, fn: CheckFn) -> tuple[str, dict[str, Any]]:
        start = time.perf_counter()
        try:
            await asyncio.wait_for(fn(settings), timeout=timeout)
        except Exception as exc:  # noqa: BLE001 - report any failure as unhealthy
            error = "timeout" if isinstance(exc, TimeoutError) else f"{type(exc).__name__}: {exc}"
            return name, {"ok": False, "error": error}
        return name, {"ok": True, "latency_ms": round((time.perf_counter() - start) * 1000, 1)}

    results = dict(await asyncio.gather(*(run_one(n, f) for n, f in checks.items())))
    return {"ok": all(r["ok"] for r in results.values()), "checks": results}
