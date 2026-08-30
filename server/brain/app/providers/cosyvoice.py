import io
import logging
import struct
from typing import AsyncGenerator

import httpx

from app.core.config import settings

log = logging.getLogger("bmo.cosyvoice")


class CosyVoiceProvider:
    """
    HTTP client for a CosyVoice FastAPI service (runtime/python/fastapi/server.py).
    The CosyVoice server must be running separately — see docker-compose.yml.

    Modes (COSYVOICE_MODE):
      'sft'        — built-in speaker; set COSYVOICE_SPEAKER (e.g. "英文女")
      'zero_shot'  — voice clone from COSYVOICE_REFERENCE_AUDIO + COSYVOICE_PROMPT_TEXT
      'instruct'   — sft + COSYVOICE_INSTRUCT_TEXT for emotion/style control

    The server returns raw int16 mono PCM as a streaming octet-stream.
    All endpoints use Form parameters (multipart for zero_shot, urlencoded otherwise).
    """

    @classmethod
    def _url(cls) -> str:
        return settings.COSYVOICE_URL.rstrip("/")

    @classmethod
    async def _stream_raw_pcm(cls, text: str) -> AsyncGenerator[bytes, None]:
        """Yields raw int16 mono PCM bytes streamed from the CosyVoice service."""
        mode = settings.COSYVOICE_MODE
        endpoint = f"{cls._url()}/inference_{mode}"

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0)
        ) as client:
            if mode == "zero_shot":
                ref_path = settings.COSYVOICE_REFERENCE_AUDIO
                try:
                    with open(ref_path, "rb") as fh:
                        ref_bytes = fh.read()
                except FileNotFoundError:
                    raise FileNotFoundError(
                        f"CosyVoice reference audio not found: {ref_path!r}. "
                        "Place a clean voice sample at COSYVOICE_REFERENCE_AUDIO."
                    )
                # zero_shot uses multipart: form fields + wav file
                files = {"prompt_wav_upload": ("reference.wav", ref_bytes, "audio/wav")}
                form = {
                    "tts_text": text,
                    "prompt_text": settings.COSYVOICE_PROMPT_TEXT,
                }
                async with client.stream("POST", endpoint, data=form, files=files) as resp:
                    resp.raise_for_status()
                    async for chunk in resp.aiter_bytes(4096):
                        if chunk:
                            yield chunk
            else:
                # sft / instruct — url-encoded form body
                form = {"tts_text": text, "spk_id": settings.COSYVOICE_SPEAKER}
                if mode == "instruct":
                    form["instruct_text"] = settings.COSYVOICE_INSTRUCT_TEXT
                async with client.stream("POST", endpoint, data=form) as resp:
                    resp.raise_for_status()
                    async for chunk in resp.aiter_bytes(4096):
                        if chunk:
                            yield chunk

    @classmethod
    async def synthesize(cls, text: str, output_path: str) -> None:
        """Full synthesis — collects all audio and writes a single WAV file."""
        pcm_parts: list[bytes] = []
        async for raw in cls._stream_raw_pcm(text):
            pcm_parts.append(raw)
        all_pcm = b"".join(pcm_parts)
        with open(output_path, "wb") as f:
            f.write(_pcm_to_wav(all_pcm, settings.COSYVOICE_SAMPLE_RATE))
        log.info("CosyVoice synthesized %d PCM bytes → %s", len(all_pcm), output_path)

    @classmethod
    async def synthesize_stream(cls, text: str) -> AsyncGenerator[bytes, None]:
        """
        Streaming synthesis — yields self-contained WAV chunks (~0.5s each)
        as the CosyVoice service produces audio.
        """
        # 0.5s of int16 mono PCM per yielded chunk
        chunk_bytes = settings.COSYVOICE_SAMPLE_RATE  # rate * 1ch * 2bytes / 2 = rate bytes
        buf = bytearray()
        async for raw in cls._stream_raw_pcm(text):
            buf.extend(raw)
            while len(buf) >= chunk_bytes:
                out = bytes(buf[:chunk_bytes])
                del buf[:chunk_bytes]
                yield _pcm_to_wav(out, settings.COSYVOICE_SAMPLE_RATE)
        if buf:
            yield _pcm_to_wav(bytes(buf), settings.COSYVOICE_SAMPLE_RATE)


def _pcm_to_wav(pcm: bytes, sample_rate: int) -> bytes:
    """Wrap raw int16 mono PCM in a WAV container."""
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
