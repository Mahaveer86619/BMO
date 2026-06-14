import asyncio
import io
import logging
import os
import struct
import threading
from typing import AsyncGenerator

import numpy as np

from app.core.config import settings

log = logging.getLogger("bmo.kokoro")

_SAMPLE_RATE = 24000  # Kokoro-82M native output rate


class KokoroProvider:
    """
    Kokoro-82M TTS — flow-matching model that runs well on CPU.
    Yields one WAV chunk per sentence, so streaming starts immediately
    and the client can begin playing while later sentences are still generating.

    Voices (KOKORO_VOICE):
      American Female : af_sky  af_bella  af_nicole  af_heart
      American Male   : am_adam  am_michael
      British Female  : bf_emma  bf_isabella
      British Male    : bm_george  bm_lewis
    """

    _pipeline = None
    _lock = threading.Lock()

    @classmethod
    def _get_pipeline(cls):
        if cls._pipeline is None:
            with cls._lock:
                if cls._pipeline is None:
                    os.environ.setdefault("HF_HOME", settings.KOKORO_CACHE_DIR)
                    from kokoro import KPipeline
                    log.info("Loading Kokoro pipeline (lang=%s)...", settings.KOKORO_LANG)
                    cls._pipeline = KPipeline(lang_code=settings.KOKORO_LANG)
                    log.info("Kokoro ready.")
        return cls._pipeline

    @classmethod
    def _iter_chunks(cls, text: str):
        """Sync generator — yields WAV bytes, one per sentence chunk."""
        pipeline = cls._get_pipeline()
        for _, _, audio in pipeline(
            text,
            voice=settings.KOKORO_VOICE,
            speed=settings.KOKORO_SPEED,
        ):
            if audio is None or len(audio) == 0:
                continue
            yield _pcm_to_wav(_to_pcm(audio), _SAMPLE_RATE)

    @classmethod
    def synthesize(cls, text: str, output_path: str) -> None:
        """Full synthesis — writes a single WAV file (used by HTTP /talk and fillers)."""
        pcm_parts: list[bytes] = []
        pipeline = cls._get_pipeline()
        for _, _, audio in pipeline(
            text,
            voice=settings.KOKORO_VOICE,
            speed=settings.KOKORO_SPEED,
        ):
            if audio is not None and len(audio) > 0:
                pcm_parts.append(_to_pcm(audio))
        all_pcm = b"".join(pcm_parts)
        with open(output_path, "wb") as f:
            f.write(_pcm_to_wav(all_pcm, _SAMPLE_RATE))

    @classmethod
    async def synthesize_stream(cls, text: str) -> AsyncGenerator[bytes, None]:
        """
        Async generator — yields one WAV chunk per sentence as Kokoro generates it.
        Runs the sync pipeline in a thread to keep the event loop free.
        """
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _producer():
            try:
                for wav in cls._iter_chunks(text):
                    loop.call_soon_threadsafe(queue.put_nowait, wav)
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        t = threading.Thread(target=_producer, daemon=True)
        t.start()

        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item


def _to_pcm(audio) -> bytes:
    """Convert Kokoro output (PyTorch Tensor or NumPy array) to int16 PCM bytes."""
    if hasattr(audio, 'detach'):
        audio = audio.detach().cpu().numpy()
    return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16).tobytes()


def _pcm_to_wav(pcm: bytes, sample_rate: int) -> bytes:
    data_size = len(pcm)
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(pcm)
    return buf.getvalue()
