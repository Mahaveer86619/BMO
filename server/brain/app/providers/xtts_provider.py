import asyncio
import io
import logging
import os
import struct
import threading
from typing import AsyncGenerator

import numpy as np

from app.core.config import settings

log = logging.getLogger("bmo.xtts")

_SAMPLE_RATE = 24000  # XTTS v2 native output rate


class XTTSProvider:
    _model = None
    _gpt_cond_latent = None
    _speaker_embedding = None

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            from TTS.api import TTS

            os.environ.setdefault("TTS_HOME", settings.XTTS_CACHE_DIR)
            os.environ["COQUI_TOS_AGREED"] = "1"
            log.info("Loading XTTS v2 model (first load downloads ~1.8GB)...")
            cls._model = TTS(
                "tts_models/multilingual/multi-dataset/xtts_v2",
                gpu=False,
                progress_bar=True,
            )
            log.info("XTTS v2 ready.")
        return cls._model

    @classmethod
    def _get_latents(cls, reference_audio: str):
        """Compute + cache voice conditioning latents from reference.wav.
        Expensive once, free on every subsequent call."""
        if cls._gpt_cond_latent is None:
            if not os.path.exists(reference_audio):
                raise FileNotFoundError(
                    f"BMO reference audio not found at {reference_audio!r}. "
                    "Add a 30-60s clean BMO clip to brain/data/bmo_voice/reference.wav"
                )
            tts_model = cls._get_model().synthesizer.tts_model
            log.info("Computing voice conditioning latents (cached after this)...")
            cls._gpt_cond_latent, cls._speaker_embedding = (
                tts_model.get_conditioning_latents(audio_path=[reference_audio])
            )
            log.info("Conditioning latents cached.")
        return cls._gpt_cond_latent, cls._speaker_embedding

    @classmethod
    def synthesize(cls, text: str, output_path: str, reference_audio: str) -> None:
        """Full synthesis to file — used by the HTTP /talk endpoint."""
        if not os.path.exists(reference_audio):
            raise FileNotFoundError(f"BMO reference audio not found at {reference_audio!r}.")
        cls._get_model().tts_to_file(
            text=text,
            speaker_wav=reference_audio,
            language="en",
            file_path=output_path,
        )

    @classmethod
    def _stream_sync(cls, text: str, reference_audio: str):
        """Sync generator — yields WAV bytes per chunk. Run in a thread."""
        gpt_cond_latent, speaker_embedding = cls._get_latents(reference_audio)
        tts_model = cls._get_model().synthesizer.tts_model

        chunks = tts_model.inference_stream(
            text=text,
            language="en",
            gpt_cond_latent=gpt_cond_latent,
            speaker_embedding=speaker_embedding,
            stream_chunk_size=20,
            temperature=0.7,
            enable_text_splitting=True,
        )
        for chunk in chunks:
            audio_np = chunk.squeeze().cpu().numpy()
            pcm = (np.clip(audio_np, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
            yield _pcm_to_wav(pcm, _SAMPLE_RATE)

    @classmethod
    async def synthesize_stream(
        cls, text: str, reference_audio: str
    ) -> AsyncGenerator[bytes, None]:
        """
        Async generator — yields WAV chunks as XTTS generates them.
        The first chunk typically arrives within a few seconds, long before
        the full response would be ready with non-streaming synthesis.
        """
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _producer():
            try:
                for wav in cls._stream_sync(text, reference_audio):
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
