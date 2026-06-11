import logging
import asyncpg
from app.core.config import settings

log = logging.getLogger("bmo.db")

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    global _pool
    if not settings.DATABASE_URL:
        log.warning("DATABASE_URL not set — DB features (reminders) are disabled.")
        return
    try:
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=1,
            max_size=5,
            command_timeout=10,
        )
        await _apply_schema(_pool)
        log.info("DB pool ready.")
    except Exception as e:
        log.error("DB init failed: %s — DB features disabled.", e)
        _pool = None


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        log.info("DB pool closed.")


def get_pool() -> "asyncpg.Pool | None":
    return _pool


async def _apply_schema(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id          SERIAL PRIMARY KEY,
                text        TEXT        NOT NULL,
                when_text   TEXT,
                remind_at   TIMESTAMPTZ,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                delivered   BOOLEAN     NOT NULL DEFAULT FALSE
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                id            SERIAL       PRIMARY KEY,
                name          VARCHAR(100) NOT NULL UNIQUE,
                ip_address    TEXT         NOT NULL,
                port          INTEGER      NOT NULL DEFAULT 8080,
                active        BOOLEAN      NOT NULL DEFAULT TRUE,
                wake_word     VARCHAR(50),
                last_seen     TIMESTAMPTZ,
                registered_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id           SERIAL       PRIMARY KEY,
                created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                transcript   TEXT,
                command      VARCHAR(50),
                payload      TEXT,
                reply        TEXT,
                audio_key    TEXT,
                latency_ms   INTEGER,
                tts_provider VARCHAR(20)
            )
        """)
    log.info("DB schema applied.")
