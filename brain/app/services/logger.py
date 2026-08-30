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
    input_audio_key: str | None = None,
    audio_key: str | None = None,
    latency_ms: int,
) -> None:
    """
    Persist one turn to the interactions table.
    Silently skips if the DB pool is not available.

    input_audio_key is the raw mic capture (what was actually said); audio_key
    is the synthesized response WAV — only set on /talk (HTTP), since /ws/talk
    streams TTS in chunks with no single consolidated response file.
    """
    pool = get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO interactions
                    (transcript, command, payload, reply, input_audio_key, audio_key, latency_ms, tts_provider)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                transcript,
                command,
                payload,
                reply,
                input_audio_key,
                audio_key,
                latency_ms,
                settings.TTS_PROVIDER,
            )
        log.debug(
            "Interaction logged — cmd=%r  latency=%dms  input=%s  audio=%s",
            command, latency_ms, input_audio_key or "none", audio_key or "none",
        )
    except Exception as e:
        log.warning("Failed to log interaction: %s", e)
