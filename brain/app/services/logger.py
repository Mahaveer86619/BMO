import logging

from app.core.config import settings
from app.db.client import get_pool

log = logging.getLogger("bmo.logger")


async def log_interaction(
    *,
    transcript: str,
    command: str,
    payload: str,
    reply: str,
    audio_key: str | None,
    latency_ms: int,
) -> None:
    """
    Persist one turn to the interactions table.
    Silently skips if the DB pool is not available.
    """
    pool = get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO interactions
                    (transcript, command, payload, reply, audio_key, latency_ms, tts_provider)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                transcript,
                command,
                payload,
                reply,
                audio_key,
                latency_ms,
                settings.TTS_PROVIDER,
            )
        log.debug(
            "Interaction logged — cmd=%r  latency=%dms  audio=%s",
            command, latency_ms, audio_key or "none",
        )
    except Exception as e:
        log.warning("Failed to log interaction: %s", e)
