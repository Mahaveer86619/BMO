import asyncio
import logging
import os
import tempfile
from app.providers.whisper import WhisperProvider
from app.providers.hf_whisper import HFWhisperProvider
from app.providers.ollama import OllamaProvider
from app.providers.piper import PiperProvider
from app.utils.audio import normalize_audio
from app.nlp.intent import detect_intent, handle_intent
from app.core.config import settings

log = logging.getLogger("bmo.brain")


class BrainService:
    @staticmethod
    async def process_talk(audio_bytes: bytes) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as in_f:
            in_f.write(audio_bytes)
            input_path = in_f.name

        output_path = input_path + "_reply.wav"
        try:
            # 1. STT — CPU-bound, run off the event loop
            if settings.STT_PROVIDER == "huggingface":
                text = await HFWhisperProvider.transcribe(input_path)
            else:
                text = await asyncio.to_thread(WhisperProvider.transcribe, input_path)

            if not text:
                text = "..."

            log.info("STT  → %r", text)

            # 2. NLP layer — instant, runs on event loop
            intent = detect_intent(text)
            log.info("NLP  → intent=%r", intent)
            reply = handle_intent(intent) if intent else None

            # 3. LLM fallback — async HTTP, yields to event loop while waiting
            if not reply:
                log.info("LLM  → calling Ollama")
                reply = await OllamaProvider.generate_response(text)
                log.info("LLM  → %r", reply)
            else:
                log.info("NLP  → %r (LLM skipped)", reply)

            # 4. TTS — subprocess, run off the event loop
            log.info("TTS  → synthesizing")
            await asyncio.to_thread(
                PiperProvider.synthesize, reply, output_path, settings.PIPER_MODEL_PATH
            )

            with open(output_path, "rb") as out_f:
                reply_audio = out_f.read()

            return normalize_audio(reply_audio)

        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
