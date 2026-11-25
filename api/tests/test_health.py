import asyncio
import os

import pytest
from fastapi.testclient import TestClient

from app import health, main, storage
from app.config import get_settings


async def _ok(settings):
    return None


async def _fail(settings):
    raise ConnectionError("refused")


async def _hang(settings):
    await asyncio.sleep(10)


async def test_run_checks_reports_each_dependency():
    result = await health.run_checks(
        get_settings(), {"a": _ok, "b": _fail, "c": _hang}, timeout=0.05
    )
    assert result["ok"] is False
    assert result["checks"]["a"]["ok"] is True
    assert "latency_ms" in result["checks"]["a"]
    assert result["checks"]["b"] == {"ok": False, "error": "ConnectionError: refused"}
    assert result["checks"]["c"] == {"ok": False, "error": "timeout"}


async def test_run_checks_all_ok():
    result = await health.run_checks(get_settings(), {"a": _ok, "b": _ok})
    assert result["ok"] is True


@pytest.fixture
def client(monkeypatch):
    async def no_bucket(settings):
        return None

    monkeypatch.setattr(storage, "ensure_bucket", no_bucket)
    with TestClient(main.app) as c:
        yield c


def test_live(client):
    assert client.get("/health/live").json() == {"status": "ok"}


def test_ready_returns_503_when_a_dependency_is_down(client, monkeypatch):
    monkeypatch.setattr(health, "DEFAULT_CHECKS", {"postgres": _ok, "redis": _fail})
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["checks"]["redis"]["ok"] is False


def test_ready_returns_200_when_all_ok(client, monkeypatch):
    monkeypatch.setattr(health, "DEFAULT_CHECKS", {"postgres": _ok, "redis": _ok})
    assert client.get("/health/ready").status_code == 200


def test_retention_policy_expires_after_configured_days():
    rule = storage.retention_policy(30)["Rules"][0]
    assert rule["ID"] == storage.RETENTION_RULE_ID
    assert rule["Expiration"] == {"Days": 30}


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("INTEGRATION") != "1", reason="set INTEGRATION=1 with the stack running"
)
async def test_real_dependencies_are_ready(monkeypatch):
    # Use the real .env instead of the unit-test values.
    for key in ("POSTGRES_PASSWORD", "REDIS_PASSWORD", "S3_ACCESS_KEY", "S3_SECRET_KEY"):
        monkeypatch.delenv(key)
    get_settings.cache_clear()
    settings = get_settings()
    await storage.ensure_bucket(settings)
    result = await health.run_checks(settings)
    assert result["ok"], result
