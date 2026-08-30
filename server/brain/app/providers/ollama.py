import logging
import httpx
from app.core.config import settings
from app.core.prompt import BMO_SYSTEM_PROMPT

log = logging.getLogger("bmo.ollama")


class OllamaProvider:

    @staticmethod
    async def generate_response(prompt: str) -> str:
        """Single-turn chat — system prompt + user message, no tools."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{settings.OLLAMA_URL}/api/chat",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": BMO_SYSTEM_PROMPT},
                        {"role": "user",   "content": prompt},
                    ],
                    "stream": False,
                },
            )
            r.raise_for_status()
        return (r.json()["message"].get("content") or "").strip()

    @staticmethod
    async def chat(messages: list[dict]) -> str:
        """Multi-turn /api/chat without tools. Returns assistant text."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{settings.OLLAMA_URL}/api/chat",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                },
            )
            r.raise_for_status()
        return (r.json()["message"].get("content") or "").strip()

