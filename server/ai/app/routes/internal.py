import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..compute import detect_compute_mode
from ..config import settings
from ..llm.router import get_provider

router = APIRouter(prefix="/internal", tags=["internal"])


class ChatRequest(BaseModel):
    messages: list[dict[str, str]]
    tier: str = "fast"


class ChatResponse(BaseModel):
    reply: str
    tier: str


@router.get("/health")
def health():
    """Checks Ollama too, now that it's a bundled process rather than an
    external dependency (see supervisord.conf) — mirrors the 200/503 pattern
    of Go's own /api/v1/health so a bad Ollama shows up transitively there."""
    services = {"ai": "healthy"}
    try:
        resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3.0)
        services["ollama"] = "healthy" if resp.status_code == 200 else "unhealthy"
    except Exception:
        services["ollama"] = "unhealthy"

    overall = "healthy" if all(v == "healthy" for v in services.values()) else "unhealthy"
    status_code = 200 if overall == "healthy" else 503
    return JSONResponse(status_code=status_code, content={"status": overall, "services": services})


@router.get("/status")
def status():
    return {
        "compute_mode": detect_compute_mode(settings.compute_mode_override),
        "cloud_enabled": settings.llm_provider_cloud_enabled,
        "ollama_base_url": settings.ollama_base_url,
    }


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        provider = get_provider(req.tier)  # type: ignore[arg-type]
        reply = provider.chat(req.messages)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ChatResponse(reply=reply, tier=req.tier)


@router.post("/stt")
def speech_to_text():
    """Placeholder — faster-whisper wiring goes here, see notes/Software.md#Server Stack.
    Not implemented yet."""
    raise HTTPException(status_code=501, detail="STT not implemented yet")


@router.post("/tts")
def text_to_speech():
    """Placeholder — Piper/XTTS wiring goes here, see notes/Software.md#Phase 1.5.
    Not implemented yet."""
    raise HTTPException(status_code=501, detail="TTS not implemented yet")
