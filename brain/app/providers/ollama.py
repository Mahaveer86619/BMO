import httpx
from app.core.config import settings
from app.core.prompt import BMO_SYSTEM_PROMPT


class OllamaProvider:
    @staticmethod
    async def generate_response(prompt: str) -> str:
        url = f"{settings.OLLAMA_URL}/api/generate"
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "system": BMO_SYSTEM_PROMPT,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        return response.json().get("response", "")
