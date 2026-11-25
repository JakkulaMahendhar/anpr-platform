from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables or the repo's .env."""

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "anpr"
    postgres_password: SecretStr
    postgres_db: str = "anpr"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: SecretStr

    # Empty endpoint = real AWS S3; otherwise any S3-compatible service.
    s3_endpoint_url: str | None = "http://localhost:8333"
    s3_region: str = "us-east-1"
    s3_access_key: str
    s3_secret_key: SecretStr
    s3_bucket: str = "anpr-images"
    image_retention_days: int = Field(default=30, ge=0)

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password.get_secret_value()}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
