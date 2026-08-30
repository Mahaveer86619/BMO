import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from app.core.connections import registry
from app.db.client import get_pool

log = logging.getLogger("bmo.control")
router = APIRouter()


# ── WebSocket control channel ──────────────────────────────────────────────────

@router.websocket("/ws/control")
async def ws_control(websocket: WebSocket):
    """
    Persistent bidirectional control channel.  Each BMO Pico W opens one
    connection here and immediately sends a 'register' message.

    Pico → Server:
      {"type": "register", "name": "desk-bmo", "ip": "192.168.1.5", "port": 8080}
      {"type": "state",    "state": "IDLE|LISTENING|THINKING|SPEAKING|REARMING"}
      {"type": "pong"}

    Server → Pico:
      {"type": "registered", "bot_id": 1, "active": true, "wake_word": "lumi"}
      {"type": "ping"}
      {"type": "wake"}        — start listening immediately
      {"type": "config",      "active": true|false}
    """
    await registry.accept(websocket)
    bot_id: int | None = None

    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
            except asyncio.TimeoutError:
                alive = await registry.send_to(bot_id, {"type": "ping"}) if bot_id else False
                if not alive:
                    break
                continue

            msg_type = msg.get("type")

            if msg_type == "register":
                name = msg.get("name", "unknown")
                ip   = msg.get("ip",   websocket.client.host if websocket.client else "unknown")
                port = int(msg.get("port", 8080))

                row = await _upsert_bot(name, ip, port)
                if row is None:
                    await websocket.send_json({"type": "error", "message": "DB unavailable."})
                    break

                bot_id = row["id"]
                await registry.register(websocket, bot_id)
                await websocket.send_json({
                    "type":      "registered",
                    "bot_id":    bot_id,
                    "active":    row["active"],
                    "wake_word": row["wake_word"],
                })
                log.info("Bot %r registered — id=%d  ip=%s  active=%s", name, bot_id, ip, row["active"])

            elif msg_type == "state":
                state = msg.get("state", "?")
                log.info("Bot %s state → %s", bot_id, state)
                if bot_id:
                    await _touch_last_seen(bot_id)

            elif msg_type == "pong":
                pass

            else:
                log.warning("Unknown control message from bot %s: %s", bot_id, msg)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.error("Control channel error (bot %s): %s", bot_id, e)
    finally:
        registry.disconnect(websocket)


# ── Bot management HTTP endpoints ──────────────────────────────────────────────

@router.get("/bots")
async def list_bots():
    """List all registered bots with their online status."""
    pool = get_pool()
    if pool is None:
        return JSONResponse({"error": "DB unavailable."}, status_code=503)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, ip_address, port, active, wake_word, last_seen, registered_at "
            "FROM bots ORDER BY registered_at DESC"
        )

    return [
        {**dict(r), "online": registry.is_online(r["id"])}
        for r in rows
    ]


@router.get("/bots/{bot_id}")
async def get_bot(bot_id: int):
    pool = get_pool()
    if pool is None:
        return JSONResponse({"error": "DB unavailable."}, status_code=503)

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM bots WHERE id = $1", bot_id)

    if row is None:
        return JSONResponse({"error": "Bot not found."}, status_code=404)

    return {**dict(row), "online": registry.is_online(bot_id)}


@router.post("/bots/{bot_id}/wake")
async def wake_bot(bot_id: int):
    """Send an immediate wake command to a specific bot."""
    sent = await registry.send_to(bot_id, {"type": "wake"})
    if not sent:
        return JSONResponse({"ok": False, "error": f"Bot {bot_id} is not connected."}, status_code=503)
    log.info("Wake sent to bot %d.", bot_id)
    return {"ok": True}


@router.post("/bots/{bot_id}/activate")
async def activate_bot(bot_id: int):
    """Mark bot as active and push the config update if it is online."""
    ok = await _set_active(bot_id, True)
    if not ok:
        return JSONResponse({"error": "Bot not found."}, status_code=404)
    await registry.send_to(bot_id, {"type": "config", "active": True})
    log.info("Bot %d activated.", bot_id)
    return {"ok": True, "bot_id": bot_id, "active": True}


@router.post("/bots/{bot_id}/deactivate")
async def deactivate_bot(bot_id: int):
    """Mark bot as inactive and push the config update if it is online."""
    ok = await _set_active(bot_id, False)
    if not ok:
        return JSONResponse({"error": "Bot not found."}, status_code=404)
    await registry.send_to(bot_id, {"type": "config", "active": False})
    log.info("Bot %d deactivated.", bot_id)
    return {"ok": True, "bot_id": bot_id, "active": False}


# ── Legacy single-bot wake (backward compat) ───────────────────────────────────

@router.post("/wake")
async def wake_any():
    """Wake the first connected bot. Kept for backward compatibility."""
    ids = registry.online_ids()
    if not ids:
        return JSONResponse({"ok": False, "error": "No bot connected."}, status_code=503)
    sent = await registry.send_to(ids[0], {"type": "wake"})
    return {"ok": sent, "bot_id": ids[0]}


# ── DB helpers ─────────────────────────────────────────────────────────────────

async def _upsert_bot(name: str, ip: str, port: int):
    pool = get_pool()
    if pool is None:
        return None
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """
            INSERT INTO bots (name, ip_address, port, last_seen)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (name) DO UPDATE
              SET ip_address = EXCLUDED.ip_address,
                  port       = EXCLUDED.port,
                  last_seen  = NOW()
            RETURNING id, active, wake_word
            """,
            name, ip, port,
        )


async def _touch_last_seen(bot_id: int) -> None:
    pool = get_pool()
    if pool is None:
        return
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE bots SET last_seen = NOW() WHERE id = $1", bot_id
        )


async def _set_active(bot_id: int, active: bool) -> bool:
    pool = get_pool()
    if pool is None:
        return False
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE bots SET active = $1 WHERE id = $2", active, bot_id
        )
    return result != "UPDATE 0"
