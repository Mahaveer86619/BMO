import httpx
from app.core.config import settings
from app.core.state import state
from app.nlp.commands import build_llm_prompt, handle_direct, route
from app.providers.ollama import OllamaProvider


class ChatService:
    @staticmethod
    async def process_text(text: str) -> tuple[str, str]:
        """Returns (reply, source). LUMI gate is bypassed for text input."""
        command, payload = route(text, require_lumi=False)

        if command == "silence":
            return "I didn't catch a command there. Try starting with LUMI!", "nlp"

        direct = handle_direct(command, payload)
        if direct is not None:
            return direct, "nlp"

        prompt = build_llm_prompt(command, payload)
        return await OllamaProvider.generate_response(prompt), "llm"

    @staticmethod
    async def status() -> dict:
        ollama_ok = False
        ollama_error = None
        models = []
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{settings.OLLAMA_URL}/api/tags")
                ollama_ok = r.status_code == 200
                models = [m["name"] for m in r.json().get("models", [])]
        except Exception as e:
            ollama_error = str(e)

        return {
            "server": state.as_dict(),
            "ollama": {
                "url": settings.OLLAMA_URL,
                "reachable": ollama_ok,
                "models": models,
                **({"error": ollama_error} if ollama_error else {}),
            },
            "stt_provider": settings.STT_PROVIDER,
            "whisper_model": settings.WHISPER_MODEL,
            "tts_provider": settings.TTS_PROVIDER,
            "llm_model": settings.OLLAMA_MODEL,
        }
