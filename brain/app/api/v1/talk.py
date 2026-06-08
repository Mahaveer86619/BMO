import asyncio
import base64
from fastapi import APIRouter, UploadFile, File, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from app.services.brain import BrainService
from app.services.chat import ChatService
from app.services.filler import FillerService

router = APIRouter()


@router.post("/talk")
async def talk(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    response_audio = await BrainService.process_talk(audio_bytes)
    return Response(content=response_audio, media_type="audio/wav")


class ChatRequest(BaseModel):
    text: str


@router.post("/chat")
async def chat(body: ChatRequest):
    """Text-in / text-out — tests NLP layer and Ollama without audio."""
    reply, source = await ChatService.process_text(body.text)
    return {"input": body.text, "reply": reply, "source": source}


@router.get("/status")
async def status():
    """Check connectivity to each backend service."""
    return await ChatService.status()


@router.websocket("/ws/talk")
async def ws_talk(websocket: WebSocket):
    """
    WebSocket pipeline with filler audio.

    Flow:
      client  →  raw WAV bytes
      server  ←  {"type": "filler",   "audio": "<base64 wav>"}  (immediate)
      server  ←  {"type": "filler",   "audio": "<base64 wav>"}  (every 4s while processing)
      server  ←  {"type": "response", "audio": "<base64 wav>"}  (final answer)
      server  ←  {"type": "error",    "message": "..."}         (on failure)
    """
    await websocket.accept()

    async def _send_audio(msg_type: str, audio: bytes) -> None:
        await websocket.send_json({
            "type": msg_type,
            "audio": base64.b64encode(audio).decode(),
        })

    try:
        audio_bytes = await websocket.receive_bytes()

        # Fire filler immediately — before pipeline even starts
        filler = FillerService.get_random()
        if filler:
            await _send_audio("filler", filler)

        # Drip more fillers every 4s while the pipeline runs
        stop = asyncio.Event()

        async def _drip():
            while not stop.is_set():
                try:
                    await asyncio.wait_for(stop.wait(), timeout=4.0)
                except asyncio.TimeoutError:
                    clip = FillerService.get_random()
                    if clip and not stop.is_set():
                        await _send_audio("filler", clip)

        drip_task = asyncio.create_task(_drip())

        try:
            response_audio = await BrainService.process_talk(audio_bytes)
            stop.set()
            await drip_task
            await _send_audio("response", response_audio)
        except Exception as e:
            stop.set()
            drip_task.cancel()
            await websocket.send_json({"type": "error", "message": str(e)})
        finally:
            stop.set()

    except WebSocketDisconnect:
        pass
