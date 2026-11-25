import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    """Deterministic settings for unit tests, independent of any local .env."""
    for key, value in {
        "POSTGRES_PASSWORD": "test",
        "REDIS_PASSWORD": "test",
        "S3_ACCESS_KEY": "test-user",
        "S3_SECRET_KEY": "test-password",
        "IMAGE_RETENTION_DAYS": "7",
    }.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
