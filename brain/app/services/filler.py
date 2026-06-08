import os
import random
import tempfile
from app.providers.piper import PiperProvider
from app.core.config import settings

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
        """Pre-synthesize all filler phrases at startup. Failures are silent —
        missing clips just means fewer filler options, not a crash."""
        for phrase in _PHRASES:
            path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    path = f.name
                PiperProvider.synthesize(phrase, path, settings.PIPER_MODEL_PATH)
                with open(path, "rb") as f:
                    cls._clips.append(f.read())
            except Exception:
                pass
            finally:
                if path and os.path.exists(path):
                    os.remove(path)

    @classmethod
    def get_random(cls) -> bytes | None:
        return random.choice(cls._clips) if cls._clips else None
