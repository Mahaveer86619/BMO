import httpx
from app.providers.ollama import OllamaProvider
from app.nlp.intent import detect_intent, handle_intent
from app.core.config import settings


class ChatService:
    @staticmethod
    async def process_text(text: str) -> tuple[str, str]:
        """Returns (reply, source) where source is 'nlp' or 'llm'."""
        intent = detect_intent(text)
        reply = handle_intent(intent) if intent else None
        if reply:
            return reply, "nlp"
        return await OllamaProvider.generate_response(text), "llm"

    @staticmethod
    async def status() -> dict:
        ollama_ok = False
        ollama_error = None
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{settings.OLLAMA_URL}/api/tags")
                ollama_ok = r.status_code == 200
                models = [m["name"] for m in r.json().get("models", [])]
        except Exception as e:
            ollama_error = str(e)
            models = []

        return {
            "ollama": {
                "url": settings.OLLAMA_URL,
                "reachable": ollama_ok,
                "models": models,
                **({"error": ollama_error} if ollama_error else {}),
            },
            "stt_provider": settings.STT_PROVIDER,
            "whisper_model": settings.WHISPER_MODEL,
            "llm_model": settings.OLLAMA_MODEL,
        }
