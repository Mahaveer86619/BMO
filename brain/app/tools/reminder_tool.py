import logging
from app.db.client import get_pool

log = logging.getLogger("bmo.reminder")


async def set_reminder(text: str, when: str | None = None) -> str:
    pool = get_pool()
    if pool is None:
        log.warning("Reminder requested but DB pool is not available.")
        return f"I'd love to remind you, but my memory isn't connected right now. Note: {text}."

    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO reminders (text, when_text) VALUES ($1, $2)",
            text,
            when or None,
        )

    log.info("Reminder saved: %r at %r", text, when)
    when_str = f" for {when}" if when else ""
    return f"Reminder saved{when_str}: {text}."


async def list_reminders() -> list[dict]:
    pool = get_pool()
    if pool is None:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, text, when_text, created_at, delivered FROM reminders ORDER BY created_at DESC LIMIT 20"
        )
    return [dict(r) for r in rows]
