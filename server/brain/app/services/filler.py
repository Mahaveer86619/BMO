import asyncio
import logging
import os
import random
import tempfile

from app.core.config import settings
from app.providers.piper import PiperProvider
from app.utils.audio import pad_wav

log = logging.getLogger("bmo.filler")

_PHRASES = [
    "Hmm...",
    "Let me think...",
    "One moment...",
    "Interesting...",
    "Ah, let me see...",
    "Give me a second...",
]


class FillerService:
    _clips: list[bytes] = []

    @classmethod
    async def load(cls) -> None:
        """
        Pre-synthesize all filler phrases at startup.
        Matches TTS_PROVIDER so fillers sound consistent with the main voice.
        Falls back silently per phrase so a single failure doesn't break all fillers.
        """
        provider = settings.TTS_PROVIDER
        if provider == "cosyvoice":
            from app.providers.cosyvoice import CosyVoiceProvider
            log.info("Synthesizing fillers with CosyVoice...")
        elif provider == "kokoro":
            from app.providers.kokoro_provider import KokoroProvider
            log.info("Synthesizing fillers with Kokoro (voice=%s)...", settings.KOKORO_VOICE)
        elif provider == "xtts":
            from app.providers.xtts_provider import XTTSProvider
            log.info("Synthesizing fillers with XTTS (BMO voice)...")
        else:
            log.info("Synthesizing fillers with Piper...")

        for phrase in _PHRASES:
            path = None
            try:
                path = tempfile.mktemp(suffix=".wav")
                if provider == "cosyvoice":
                    await CosyVoiceProvider.synthesize(phrase, path)
                elif provider == "kokoro":
                    await asyncio.to_thread(KokoroProvider.synthesize, phrase, path)
                elif provider == "xtts":
                    await asyncio.to_thread(
                        XTTSProvider.synthesize, phrase, path, settings.XTTS_REFERENCE_AUDIO
                    )
                else:
                    await asyncio.to_thread(
                        PiperProvider.synthesize, phrase, path, settings.PIPER_MODEL_PATH
                    )
                with open(path, "rb") as f:
                    cls._clips.append(pad_wav(f.read(), pre_ms=100, post_ms=300))
                log.info("  ✓ %r", phrase)
            except Exception as e:
                log.warning("  ✗ %r — %s (skipped)", phrase, e)
            finally:
                if path and os.path.exists(path):
                    os.remove(path)

        log.info("Fillers ready: %d/%d clips loaded.", len(cls._clips), len(_PHRASES))

    @classmethod
    def get_random(cls) -> bytes | None:
        return random.choice(cls._clips) if cls._clips else None
