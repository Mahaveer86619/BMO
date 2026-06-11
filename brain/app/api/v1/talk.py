import asyncio
import base64
import logging
import os
import tempfile

from fastapi import APIRouter, Response, UploadFile, File, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

log = logging.getLogger("bmo.ws")

from app.core.config import settings
from app.providers.piper import PiperProvider
from app.providers.xtts_provider import XTTSProvider
from app.services.brain import BrainService
from app.services.chat import ChatService
from app.services.filler import FillerService
from app.utils.audio import normalize_audio, silence_wav

router = APIRouter()


# ── HTTP endpoints ─────────────────────────────────────────────────────────────

@router.post("/talk")
async def talk(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    response_audio = await BrainService.process_talk(audio_bytes)
    return Response(content=response_audio, media_type="audio/wav")


class ChatRequest(BaseModel):
    text: str


@router.post("/chat")
async def chat(body: ChatRequest):
    """Text-in / text-out — tests command layer and Ollama without audio."""
    reply, source = await ChatService.process_text(body.text)
    return {"input": body.text, "reply": reply, "source": source}


@router.get("/status")
async def status():
    return await ChatService.status()


# ── WebSocket ──────────────────────────────────────────────────────────────────

@router.websocket("/ws/talk")
async def ws_talk(websocket: WebSocket):
    """
    Streaming audio pipeline. One persistent connection, many turns.

    Client → Server:  raw WAV bytes (one message per turn)

    Server → Client:
      {"type": "transcript", "text": "..."}          what you said
      {"type": "filler",     "audio": "<b64 wav>"}   thinking clip (repeats every 4s)
      {"type": "chunk",      "audio": "<b64 wav>"}   TTS stream chunk (starts when LLM done)
      {"type": "reply",      "text": "..."}           BMO's text reply
      {"type": "silence"}                             ignored (no LUMI / no match)
      {"type": "done"}                                end of turn
      {"type": "error",      "message": "..."}        something broke
    """
    await websocket.accept()

    async def _send_audio(msg_type: str, audio: bytes) -> None:
        await websocket.send_json({
            "type": msg_type,
            "audio": base64.b64encode(audio).decode(),
        })

    async def _drip(stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=4.0)
            except asyncio.TimeoutError:
                clip = FillerService.get_random()
                if clip and not stop.is_set():
                    await _send_audio("filler", clip)

    try:
        while True:  # Persistent connection — many turns per session
            audio_bytes = await websocket.receive_bytes()

            # ── Phase 1: filler immediately, then drip while thinking ──────────
            filler = FillerService.get_random()
            if filler:
                await _send_audio("filler", filler)

            stop = asyncio.Event()
            drip_task = asyncio.create_task(_drip(stop))

            try:
                # STT + command routing + LLM (if needed)
                reply_text, transcript, _cmd, _payload = await BrainService.process_to_text(audio_bytes)

                stop.set()
                drip_task.cancel()
                await asyncio.gather(drip_task, return_exceptions=True)

                if transcript:
                    await websocket.send_json({"type": "transcript", "text": transcript})

                if reply_text is None:
                    await websocket.send_json({"type": "silence"})
                    await websocket.send_json({"type": "done"})
                    continue

                await websocket.send_json({"type": "reply", "text": reply_text})

                # ── Phase 2: stream TTS ────────────────────────────────────────
                # Bridge silence: smooth handoff from last filler to first speech chunk
                await _send_audio("chunk", silence_wav(350))

                if settings.TTS_PROVIDER == "xtts":
                    chunk_n = 0
                    async for wav_chunk in XTTSProvider.synthesize_stream(
                        reply_text, settings.XTTS_REFERENCE_AUDIO
                    ):
                        chunk_n += 1
                        log.info("STREAM chunk #%d  %d bytes", chunk_n, len(wav_chunk))
                        await _send_audio("chunk", wav_chunk)
                else:
                    # Piper: no streaming — synthesize full then send as one chunk
                    out_path = tempfile.mktemp(suffix=".wav")
                    try:
                        await asyncio.to_thread(
                            PiperProvider.synthesize,
                            reply_text,
                            out_path,
                            settings.PIPER_MODEL_PATH,
                        )
                        with open(out_path, "rb") as f:
                            await _send_audio("chunk", normalize_audio(f.read()))
                    finally:
                        if os.path.exists(out_path):
                            os.remove(out_path)

                # Tail silence: graceful end before the connection goes idle
                await _send_audio("chunk", silence_wav(500))
                await websocket.send_json({"type": "done"})

            except Exception as e:
                stop.set()
                drip_task.cancel()
                await websocket.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        pass
