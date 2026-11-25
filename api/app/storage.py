"""S3 object storage for plate and vehicle images (SeaweedFS in dev, any S3 in prod)."""

import asyncio
import logging
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from .config import Settings

log = logging.getLogger(__name__)

RETENTION_RULE_ID = "expire-images"


def make_client(settings: Settings) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url or None,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
        config=Config(
            s3={"addressing_style": "path"},
            connect_timeout=3,
            read_timeout=5,
            retries={"max_attempts": 2},
        ),
    )


def retention_policy(days: int) -> dict:
    """Lifecycle rule that deletes every object older than `days`."""
    return {
        "Rules": [
            {
                "ID": RETENTION_RULE_ID,
                "Status": "Enabled",
                "Filter": {"Prefix": ""},
                "Expiration": {"Days": days},
            }
        ]
    }


def bucket_exists(client: Any, bucket: str) -> bool:
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchBucket", "NotFound"):
            return False
        raise
    return True


def ensure_bucket_sync(settings: Settings, client: Any | None = None) -> None:
    client = client or make_client(settings)
    bucket = settings.s3_bucket
    if not bucket_exists(client, bucket):
        client.create_bucket(Bucket=bucket)
        log.info("created bucket %s", bucket)
    if settings.image_retention_days > 0:
        client.put_bucket_lifecycle_configuration(
            Bucket=bucket,
            LifecycleConfiguration=retention_policy(settings.image_retention_days),
        )
    else:
        client.delete_bucket_lifecycle(Bucket=bucket)


async def ensure_bucket(settings: Settings) -> None:
    await asyncio.to_thread(ensure_bucket_sync, settings)
