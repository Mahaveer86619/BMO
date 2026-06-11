import asyncio
import io
import logging
import uuid
from datetime import date

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

log = logging.getLogger("bmo.storage")

_client: Minio | None = None


def _get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
    return _client


def _ensure_bucket() -> None:
    client = _get_client()
    try:
        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)
            log.info("Created MinIO bucket: %s", settings.MINIO_BUCKET)
    except S3Error as e:
        log.error("MinIO bucket init failed: %s", e)


async def upload_audio(audio_bytes: bytes) -> str | None:
    """
    Upload WAV bytes to MinIO. Returns the object key, or None on failure.
    Key format: audio/YYYY-MM-DD/<uuid>.wav
    """
    key = f"audio/{date.today().isoformat()}/{uuid.uuid4().hex}.wav"
    try:
        await asyncio.to_thread(_upload_sync, audio_bytes, key)
        log.info("Audio uploaded → %s", key)
        return key
    except Exception as e:
        log.warning("Audio upload failed: %s", e)
        return None


def _upload_sync(audio_bytes: bytes, key: str) -> None:
    _ensure_bucket()
    client = _get_client()
    client.put_object(
        settings.MINIO_BUCKET,
        key,
        io.BytesIO(audio_bytes),
        length=len(audio_bytes),
        content_type="audio/wav",
    )
