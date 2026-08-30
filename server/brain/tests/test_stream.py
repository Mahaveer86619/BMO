"""
WebSocket streaming test.
Sends a WAV file to /api/v1/ws/talk and logs every message + timing.
Saves received audio chunks to disk.

Usage (run on Windows host, needs: pip install websockets):
  python tests/test_stream.py tests/audio/02_time.wav
  python tests/test_stream.py tests/audio/01_tell_me.wav
"""

import asyncio
import base64
import struct
import sys
import time
from pathlib import Path

try:
    import websockets
except ImportError:
    sys.exit("Install websockets first:  pip install websockets")


SERVER = "ws://localhost:8000/api/v1/ws/talk"


def merge_wavs(chunks: list[bytes]) -> bytes:
    """Concatenate multiple WAV files into one by stripping all but the first header."""
    if not chunks:
        return b""
    merged_pcm = b""
    sample_rate = 24000
    for i, wav in enumerate(chunks):
        if len(wav) < 44:
            continue
        if i == 0:
            # Read sample rate from first header
            sample_rate = struct.unpack_from("<I", wav, 24)[0]
        merged_pcm += wav[44:]  # strip WAV header, keep PCM

    # Build one WAV header over the combined PCM
    data_size = len(merged_pcm)
    import io
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(merged_pcm)
    return buf.getvalue()


async def run(wav_path: Path):
    print(f"\n{'='*60}")
    print(f"Input:  {wav_path.name}  ({wav_path.stat().st_size} bytes)")
    print(f"Server: {SERVER}")
    print('='*60)

    audio_bytes = wav_path.read_bytes()
    chunks_received = []
    t0 = time.perf_counter()
    first_chunk_at = None

    async with websockets.connect(SERVER) as ws:
        print(f"[{time.perf_counter()-t0:6.2f}s] Connected")

        await ws.send(audio_bytes)
        print(f"[{time.perf_counter()-t0:6.2f}s] Sent {len(audio_bytes)} bytes")

        async for raw in ws:
            elapsed = time.perf_counter() - t0
            msg = __import__("json").loads(raw)
            mtype = msg.get("type", "?")

            if mtype in ("filler", "chunk"):
                audio = base64.b64decode(msg["audio"])
                label = "FILLER" if mtype == "filler" else "CHUNK "
                print(f"[{elapsed:6.2f}s] {label}  {len(audio):>6} bytes")
                if mtype == "chunk":
                    if first_chunk_at is None:
                        first_chunk_at = elapsed
                        print(f"           ↳ first audio chunk after {elapsed:.2f}s")
                    chunks_received.append(audio)

            elif mtype == "transcript":
                print(f"[{elapsed:6.2f}s] TRANSCRIPT  →  {msg['text']!r}")

            elif mtype == "reply":
                print(f"[{elapsed:6.2f}s] REPLY TEXT  →  {msg['text']!r}")

            elif mtype == "silence":
                print(f"[{elapsed:6.2f}s] SILENCE  (no LUMI or no command matched)")

            elif mtype == "done":
                print(f"[{elapsed:6.2f}s] DONE  —  {len(chunks_received)} chunks received")
                break

            elif mtype == "error":
                print(f"[{elapsed:6.2f}s] ERROR  →  {msg['message']}")
                break

    total = time.perf_counter() - t0
    print(f"\nTotal time: {total:.2f}s")
    if first_chunk_at:
        print(f"First audio chunk: {first_chunk_at:.2f}s  (latency before you hear anything)")

    # Save merged response
    if chunks_received:
        out = wav_path.parent / f"stream_resp_{wav_path.stem}.wav"
        out.write_bytes(merge_wavs(chunks_received))
        print(f"Saved merged response → {out}")

    print()


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/audio/02_time.wav")
    if not path.exists():
        sys.exit(f"File not found: {path}\nRun tests/run_tests.ps1 first to create test WAVs.")
    asyncio.run(run(path))
