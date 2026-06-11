import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.state import Status, state
from app.api.v1.talk import router as talk_router
from app.api.v1.control import router as control_router
from app.db.client import init_pool, close_pool

_NOISY_LOGGERS = [
    "httpcore", "httpx", "multipart", "multipart.multipart",
    "pydub", "pydub.converter", "faster_whisper",
    # uvicorn logs every WS open/close at INFO — suppress the lifecycle noise
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.protocols.websockets.websockets_impl",
]

def _configure_logging(level: str) -> None:
    if level == "verbose":
        # Everything at DEBUG — full firehose
        logging.basicConfig(level=logging.DEBUG,
                            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    elif level == "dev":
        # bmo.* pipeline steps at DEBUG, all third-party noise silenced
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
        logging.getLogger("bmo").setLevel(logging.DEBUG)
        for name in _NOISY_LOGGERS:
            logging.getLogger(name).setLevel(logging.WARNING)
    elif level == "ignore":
        logging.basicConfig(level=logging.WARNING,
                            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    else:  # alerts (default)
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

_configure_logging(settings.LOG_LEVEL)
log = logging.getLogger("bmo.startup")


class _HealthCheckFilter(logging.Filter):
    """Drop /health and /ready hits from uvicorn access log — they're just noise."""
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "/health" not in msg and "/ready" not in msg


logging.getLogger("uvicorn.access").addFilter(_HealthCheckFilter())

# Suppress WS open/close spam regardless of LOG_LEVEL
for _n in ["uvicorn.protocols.websockets",
           "uvicorn.protocols.websockets.wsproto_impl",
           "uvicorn.protocols.websockets.websockets_impl"]:
    logging.getLogger(_n).setLevel(logging.WARNING)


async def _load_models() -> None:
    """Load all models in the background so the first request is never cold."""
    try:
        # 1. Whisper STT
        log.info("Loading Whisper (%s)...", settings.WHISPER_MODEL)
        from app.providers.whisper import WhisperProvider
        await asyncio.to_thread(WhisperProvider._get_model)
        state.mark_loaded("whisper")
        log.info("Whisper ready.")

        # 2. TTS — Piper is instant, XTTS downloads ~1.8GB on first run
        if settings.TTS_PROVIDER == "xtts":
            log.info("Loading XTTS v2 (may download ~1.8GB on first run)...")
            from app.providers.xtts_provider import XTTSProvider
            await asyncio.to_thread(XTTSProvider._get_model)
            state.mark_loaded("xtts")
            log.info("XTTS ready.")
        else:
            state.mark_loaded("piper")

        # 3. Filler phrases (synthesized with Piper regardless of TTS_PROVIDER)
        log.info("Synthesizing filler phrases...")
        from app.services.filler import FillerService
        await asyncio.to_thread(FillerService.load)
        state.mark_loaded("fillers")

        state.mark_ready()
        log.info("=== BMO brain is READY === loaded=%s", state.loaded)

    except Exception as e:
        state.mark_error(str(e))
        log.error("Startup loading failed: %s", e, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB pool — awaited so it's ready before the first request
    await init_pool()
    # Model loading runs in background so Docker health checks pass immediately
    asyncio.create_task(_load_models())
    yield
    await close_pool()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.include_router(talk_router, prefix="/api/v1")
app.include_router(control_router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Liveness — always 200 if the process is alive. Used by Docker healthcheck."""
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    """Readiness — 503 while models are loading, 200 when everything is ready.
    Poll this before sending audio (e.g. from the Pico W on boot)."""
    if state.status == Status.READY:
        return state.as_dict()
    if state.status == Status.ERROR:
        return JSONResponse(state.as_dict(), status_code=503)
    return JSONResponse(state.as_dict(), status_code=503)


# Serve the web UI — mounted last so API routes always take priority
app.mount("/", StaticFiles(directory="static", html=True), name="ui")
