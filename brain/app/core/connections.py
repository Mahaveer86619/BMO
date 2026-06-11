import logging
from fastapi import WebSocket

log = logging.getLogger("bmo.connections")


class BotRegistry:
    """
    Tracks live WebSocket control connections for all connected BMO bots.

    Each bot is identified by its DB id. A bot must send a 'register' message
    immediately after connecting; until then it is held as 'pending'.

    One server → many bots. A bot reconnect silently replaces the stale socket.
    """

    def __init__(self) -> None:
        self._sockets: dict[int, WebSocket] = {}   # bot_id → WebSocket
        self._pending: list[WebSocket] = []         # connected but not yet registered

    # ── Connection lifecycle ───────────────────────────────────────────────────

    async def accept(self, ws: WebSocket) -> None:
        """Accept a new WebSocket before the bot has registered."""
        await ws.accept()
        self._pending.append(ws)

    async def register(self, ws: WebSocket, bot_id: int) -> None:
        """Promote a pending socket to a registered bot connection."""
        if ws in self._pending:
            self._pending.remove(ws)

        old = self._sockets.get(bot_id)
        if old is not None and old is not ws:
            log.warning("Bot %d reconnected — closing stale socket.", bot_id)
            try:
                await old.close()
            except Exception:
                pass

        self._sockets[bot_id] = ws
        log.info("Bot id=%d registered and online.", bot_id)

    def disconnect(self, ws: WebSocket) -> int | None:
        """Remove a socket. Returns the bot_id if it was registered, else None."""
        if ws in self._pending:
            self._pending.remove(ws)
            return None

        for bot_id, sock in list(self._sockets.items()):
            if sock is ws:
                del self._sockets[bot_id]
                log.info("Bot id=%d disconnected.", bot_id)
                return bot_id
        return None

    # ── Messaging ──────────────────────────────────────────────────────────────

    async def send_to(self, bot_id: int, msg: dict) -> bool:
        """Push a JSON message to a specific bot. Returns False if offline."""
        ws = self._sockets.get(bot_id)
        if ws is None:
            return False
        try:
            await ws.send_json(msg)
            return True
        except Exception as e:
            log.warning("Send to bot %d failed: %s — dropping connection.", bot_id, e)
            self._sockets.pop(bot_id, None)
            return False

    async def broadcast(self, msg: dict) -> int:
        """Push a message to all connected bots. Returns count of successes."""
        results = [await self.send_to(bid, msg) for bid in list(self._sockets)]
        return sum(results)

    # ── Queries ────────────────────────────────────────────────────────────────

    def is_online(self, bot_id: int) -> bool:
        return bot_id in self._sockets

    def online_ids(self) -> list[int]:
        return list(self._sockets.keys())


registry = BotRegistry()
