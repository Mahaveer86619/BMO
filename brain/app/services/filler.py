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
    def load(cls) -> None:
        """
        Pre-synthesize all filler phrases at startup.
        Uses XTTS when TTS_PROVIDER=xtts so fillers match BMO's voice.
        Falls back to Piper silently per phrase so a single failure doesn't break all fillers.
        """
        use_xtts = settings.TTS_PROVIDER == "xtts"
        if use_xtts:
            from app.providers.xtts_provider import XTTSProvider
            log.info("Synthesizing fillers with XTTS (BMO voice)...")
        else:
            log.info("Synthesizing fillers with Piper...")

        for phrase in _PHRASES:
            path = None
            try:
                path = tempfile.mktemp(suffix=".wav")
                if use_xtts:
                    XTTSProvider.synthesize(phrase, path, settings.XTTS_REFERENCE_AUDIO)
                else:
                    PiperProvider.synthesize(phrase, path, settings.PIPER_MODEL_PATH)
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
