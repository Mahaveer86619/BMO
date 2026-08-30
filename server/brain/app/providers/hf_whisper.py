import httpx
from app.core.config import settings

class HFWhisperProvider:
    """Speech-to-text via HuggingFace Inference API (free tier, adds ~200-500ms network RTT)."""

    @classmethod
    def _api_url(cls) -> str:
        return f"https://api-inference.huggingface.co/models/{settings.HF_WHISPER_MODEL}"

    @classmethod
    async def transcribe(cls, audio_path: str) -> str:
        if not settings.HF_API_TOKEN:
            raise ValueError("HF_API_TOKEN is required when STT_PROVIDER=huggingface")

        headers = {"Authorization": f"Bearer {settings.HF_API_TOKEN}"}
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(cls._api_url(), headers=headers, content=audio_bytes)
            response.raise_for_status()

        return response.json().get("text", "").strip()
