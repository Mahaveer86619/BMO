import asyncio
import logging
import os
import re
import tempfile
import time

from app.core.config import settings
from app.core.prompt import BMO_SYSTEM_PROMPT
from app.core.storage import upload_audio
from app.nlp.commands import (
    handle_direct, route,
    extract_weather_location, extract_search_query, extract_reminder_args,
)
from app.nlp.responses import TEMPLATED, format_response
from app.providers.hf_whisper import HFWhisperProvider
from app.providers.ollama import OllamaProvider
from app.providers.piper import PiperProvider
from app.providers.whisper import WhisperProvider
from app.providers.xtts_provider import XTTSProvider
from app.services.logger import log_interaction
from app.tools import time_tool, weather_tool, search_tool, reminder_tool, help_tool
from app.utils.audio import normalize_audio, silence_wav

log = logging.getLogger("bmo.brain")

_JOKE_LABEL = re.compile(r"\b(setup|punchline)\s*:\s*", re.IGNORECASE)


def _clean_llm_reply(text: str) -> str:
    """Remove artefacts that the small model emits despite instructions."""
    return _JOKE_LABEL.sub("", text).strip()


async def _transcribe(audio_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        path = f.name
    try:
        if settings.STT_PROVIDER == "huggingface":
            return await HFWhisperProvider.transcribe(path)
        return await asyncio.to_thread(WhisperProvider.transcribe, path)
    finally:
        if os.path.exists(path):
            os.remove(path)


async def _execute_intent(command: str, payload: str) -> str:
    """
    Dispatch a routed command to its handler.

    Tool commands (time/weather/search/reminder/help) are executed directly —
    no LLM involved. The LLM is called only as a last resort for open-ended
    questions and creative requests that no tool can answer.
    """
    if command == "time":
        result = time_tool.get_current_time()
        log.info("TOOL time → %r", result)
        return result

    if command == "weather":
        location = extract_weather_location(payload)
        log.info("TOOL weather → location=%r", location)
        return await weather_tool.get_weather(location)

    if command == "search":
        query = extract_search_query(payload)
        log.info("TOOL search → query=%r", query)
        return await search_tool.search_web(query)

    if command == "reminder":
        text, when = extract_reminder_args(payload)
        log.info("TOOL reminder → text=%r  when=%r", text, when)
        return await reminder_tool.set_reminder(text, when)

    if command == "help":
        return help_tool.get_help()

    # LLM: single generate_response call — no tool definitions, no two-step pipeline.
    # Handles: open-ended questions, definitions, jokes, creative requests,
    # and calculate fallback when safe_eval couldn't parse the expression.
    log.info("LLM  → generate for %r", payload[:60])
    reply = await OllamaProvider.generate_response(payload)
    reply = " ".join(reply.splitlines()).strip()  # collapse newlines — piper speaks them literally
    reply = _clean_llm_reply(reply)
    log.debug("LLM raw reply: %r", reply)
    return reply


class BrainService:

    @staticmethod
    async def process_to_text(
        audio_bytes: bytes,
    ) -> tuple[str | None, str, str, str]:
        """
        Full pipeline: audio → STT → route → execute → text reply.
        Returns (reply_text, transcript, command, payload).
        reply_text is None when input is silently ignored.
        """
        transcript = await _transcribe(audio_bytes)
        if not transcript:
            return None, "", "", ""

        log.info("STT  → %r", transcript)

        command, payload = route(transcript)
        log.info("CMD  → %r  payload=%r", command, payload)

        if command == "silence":
            return None, transcript, command, payload

        # Instant synchronous replies — no I/O
        direct = handle_direct(command, payload)
        if direct is not None:
            if command in TEMPLATED:
                direct = format_response(command, direct)
            log.info("DIRECT → %r", direct)
            return direct, transcript, command, payload

        # Dispatch to NLP tool or LLM, then shape through response template
        reply = await _execute_intent(command, payload)
        reply = format_response(command, reply)
        log.info("REPLY → %r", reply)
        return reply, transcript, command, payload

    @staticmethod
    async def process_talk(audio_bytes: bytes) -> bytes:
        """
        Full HTTP /talk pipeline: audio → text reply → TTS → audio.
        Uploads the response WAV to MinIO and logs the interaction to DB.
        Returns a normalised WAV (or silence if input was ignored).
        """
        t_start = time.monotonic()
        reply_text, transcript, command, payload = await BrainService.process_to_text(audio_bytes)

        if reply_text is None:
            return silence_wav(200)

        latency_ms = int((time.monotonic() - t_start) * 1000)

        output_path = tempfile.mktemp(suffix=".wav")
        try:
            log.info("TTS  → synthesizing via %s", settings.TTS_PROVIDER)
            if settings.TTS_PROVIDER == "xtts":
                await asyncio.to_thread(
                    XTTSProvider.synthesize,
                    reply_text,
                    output_path,
                    settings.XTTS_REFERENCE_AUDIO,
                )
            else:
                await asyncio.to_thread(
                    PiperProvider.synthesize,
                    reply_text,
                    output_path,
                    settings.PIPER_MODEL_PATH,
                )
            with open(output_path, "rb") as f:
                audio = normalize_audio(f.read())
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

        # Upload and log asynchronously — don't block the response
        audio_key = await upload_audio(audio)
        asyncio.create_task(log_interaction(
            transcript=transcript,
            command=command,
            payload=payload,
            reply=reply_text,
            audio_key=audio_key,
            latency_ms=latency_ms,
        ))

        return audio
