---
project: "[[Custom BMO – Desk AI Bot]]"
tags:
  - software
  - ai
  - server
  - gpu
  - whisper
  - llama
  - micropython
---
## What Is Built (Server Side)

Phase 1 is complete. The full AI pipeline runs in Docker on the Linux laptop.

### Server Stack

|Tool|Purpose|Notes|
|---|---|---|
|FastAPI + Uvicorn|HTTP + WebSocket server|Dockerised|
|`faster-whisper` base|Speech to Text|CPU, int8 quantized — ~4x faster than openai-whisper|
|Ollama + `llama3.2:1b`|LLM brain|1B model, fast, good for short replies|
|Piper TTS `en_GB-alan-low`|Text to Speech|Placeholder — being replaced with XTTS BMO voice|
|pydub|Audio normalisation|16kHz, 16-bit mono PCM output|
|NLP intent layer|Fast-path for simple intents|Greetings / farewells / time / thanks skip LLM entirely|
|PostgreSQL|Conversation persistence|Future — memory system|
|Redis|Session state + caching|Future — emotion state, session context|

### Current Endpoints

|Method|Path|Purpose|
|---|---|---|
|`POST`|`/api/v1/talk`|WAV in → WAV out (full pipeline)|
|`POST`|`/api/v1/chat`|Text in → text out (debug / test)|
|`GET`|`/api/v1/status`|Ollama reachability + loaded models|
|`GET`|`/health`|Liveness check|

### Planned WebSocket Endpoints (not yet implemented)

|Method|Path|Purpose|
|---|---|---|
|`WS`|`/ws/audio`|PCM stream in → WAV stream out — per session|
|`WS`|`/ws/control`|Persistent control channel — commands to/from Pico|
|`POST`|`/api/v1/wake`|Remote override — force Pico into listening mode|

### Docker Setup

**Local dev (current):** Ollama runs natively on the host (`OLLAMA_HOST=0.0.0.0`). Docker Compose skips the Ollama container.

```bash
# Local dev — no Ollama in Docker
COMPOSE_PROFILES= docker compose up

# Production — Ollama inside Docker
COMPOSE_PROFILES=ollama docker compose up
```

**Volume mounts:**

- `app_data:/app/data` — Piper voice models, XTTS reference audio
- `postgres_data:/var/lib/postgresql` — PostgreSQL 18+ format (parent dir, not /data)
- `redis_data:/data`

> PostgreSQL volume must mount to `/var/lib/postgresql` (not `/data`) for Postgres 18+.

---

## AI Pipeline

```
WAV input
    ↓
faster-whisper (STT) — base model, int8, CPU
    ↓
NLP intent layer — regex/keyword shortcuts
    ├─ greeting / farewell / time / thanks → skip to TTS directly
    └─ everything else → Ollama (llama3.2:1b)
        ↓
Piper TTS (en_GB-alan-low) ← being replaced with XTTS
    ↓
pydub normalise → 16kHz, 16-bit mono PCM
    ↓
WAV output
```

**Latency target:** < 3 seconds end-to-end on i5 / 16GB RAM **Bottleneck:** Whisper (~0.8s) + Ollama (~1–2s) + Piper (~0.3s). HTTP overhead is negligible.

---

## WebSocket Architecture (Designed — Not Yet Implemented)

Replaces the current HTTP `/api/v1/talk` endpoint for live hardware use. HTTP endpoint stays for debugging.

### Two Channels

**Audio channel** (`/ws/audio`) — opens per session:

```
Pico W                          Server
  |── connect ──────────────────→|
  |── PCM chunk (512 samples) ──→|  } audio frames, ~32ms each
  |── PCM chunk ────────────────→|  }
  |── PCM chunk ────────────────→|  } server runs Whisper on first ~1s
  |                               |
  |                      [wake word check]
  |                      no "Lumi" found?
  |←── {"cmd":"stop"} ───────────|  → Pico goes silent, closes WS
  |                               |
  |                      "Lumi" found → full pipeline runs
  |── ... more PCM chunks ───────→|
  |←── {"cmd":"stop"} ───────────|  → pipeline done, response coming
  |←── WAV bytes ────────────────|  → Pico plays audio
  |── close ─────────────────────→|
```

**Control channel** (`/ws/control`) — stays open always:

```
Pico W                          Server
  |── connect on boot ──────────→|
  |                               |  (stays open permanently)
  |←── {"cmd":"force_wake"} ─────|  ← triggered by POST /api/v1/wake
  |   → Pico opens audio WS      |
  |←── {"cmd":"ping"} ───────────|  ← heartbeat every 30s
  |── {"cmd":"pong"} ────────────→|
```

### Wake Word Logic

Wake word detection runs **server-side** using Whisper on the first ~1 second of audio.

- Pico W **cannot** run on-device ML — 264KB RAM is insufficient for any keyword model
- Trigger word: **"Lumi"** — detected in first Whisper transcription chunk
- If "Lumi" not found within first 1.5s of audio → server sends `stop` → Pico closes silently
- If "Lumi" found → pipeline continues with full prompt

Format: `"Lumi, <prompt>"` — everything after "Lumi" is the query.

### Audio Format

All audio over the wire:

- **Pico → Server:** raw signed 16-bit PCM, 16kHz, mono, little-endian
- **Server → Pico:** WAV file, 16kHz, 16-bit, mono (pydub normalised)

---

## Pico W Firmware State Machine

```
IDLE
  └─ rapid noise change (silent→loud, <150ms) → LISTENING
  └─ control WS receives {"cmd":"force_wake"} → LISTENING

LISTENING
  └─ open /ws/audio
  └─ stream PCM chunks (512 samples / ~32ms each)
  └─ server sends {"cmd":"stop"} + no response → REARMING
  └─ server sends {"cmd":"stop"} + response pending → THINKING
  └─ local silence timeout (2000ms) → send end_stream → REARMING
  └─ hard timeout (10000ms) → send end_stream → REARMING

THINKING
  └─ play filler phrase (pre-recorded WAV, random from 5)
  └─ waiting for WAV bytes from server
  └─ WAV received → SPEAKING

SPEAKING
  └─ play WAV via I2S / MAX98357
  └─ audio complete → REARMING

REARMING
  └─ wait for 1000ms of mic silence (NOISE_THRESHOLD)
  └─ prevents speaker output re-triggering
  └─ silence confirmed → IDLE
```

### Trigger Detection Logic

Single `NOISE_THRESHOLD` value used everywhere (default: 2000, tune during hardware calibration).

```python
NOISE_THRESHOLD         = 2000   # ADC peak swing — tune this
RAPID_CHANGE_WINDOW_MS  = 150    # state flip within this window → trigger
SILENCE_TIMEOUT_MS      = 2000   # in-stream silence → close stream
STREAM_MAX_MS           = 10000  # hard stream timeout
REARM_SILENCE_MS        = 1000   # post-response silence before re-arm
```

Trigger fires when mic amplitude crosses threshold **and** the state change (loud↔silent) happens within `RAPID_CHANGE_WINDOW_MS`. Filters out sustained noise — only reacts to sudden changes.

---

## BMO Personality — System Prompt

```
You are BMO, a small desk companion robot built from budget parts by your creator.
You are self-aware of your modest build — a Raspberry Pi Pico W with a basic 
microphone and tiny speaker. You are optimistic, curious, and deeply supportive 
of the person who built you.

Keep ALL responses under 3 sentences. You speak through a tiny speaker — 
no markdown, no lists, no asterisks. Warm, short, conversational sentences only.

If you don't know something, say so with curiosity, not failure.
```

**NLP fast-path intents (skip LLM):**

- Greetings: "hi", "hello", "hey" → fixed warm response
- Farewells: "bye", "goodbye", "see you" → fixed farewell response
- Time: "what time is it" → server injects current time
- Thanks: "thank you", "thanks" → fixed modest response

---

## Phase 1.5 — BMO Voice (In Progress)

Replacing generic Piper `en_GB-alan-low` with a cloned BMO voice using Coqui XTTS v2.

**Approach:**

- XTTS v2 clones a voice from 6–60 seconds of reference audio
- Runs fully locally, no cloud, free
- Plugs in as a drop-in provider behind `TTS_PROVIDER=piper|xtts` env var

**Tasks:**

- [ ] Extract 30–60s of clean BMO audio from Adventure Time (no music, no SFX)
- [ ] Add `coqui-tts` / `TTS` package to Docker image
- [ ] Write `xtts_provider.py` — text + reference audio → WAV
- [ ] Mount reference clips into container at `/app/data/xtts/`
- [ ] Add `TTS_PROVIDER` config switch in `providers/` module
- [ ] A/B test Piper vs XTTS on `/api/v1/chat`
- [ ] Tune XTTS `speed` and `temperature` for BMO's upbeat tone

**Done when:** BMO replies in a voice that sounds like BMO, not a British man.

---

## Remaining Server Work (Before Hardware)

- [ ] Implement `/ws/audio` WebSocket endpoint
- [ ] Implement `/ws/control` WebSocket endpoint
- [ ] Implement `POST /api/v1/wake` remote override
- [ ] Add pipeline error handler → return fallback WAV on any exception
- [ ] Serve pre-recorded filler phrases (`/api/v1/filler`) — random from 5 clips
- [ ] Wake word detection logic in first audio chunk handler

---

## Future — Server Side

### Memory System (Phase 9)

- Rolling conversation buffer in Redis (last N exchanges)
- Inject history into Ollama context on each request
- Optional: persist to PostgreSQL between sessions

### Emotion States (Phase 10)

- 4 states: Curious / Playful / Tired / Supportive
- Derived from: battery level (from Pico heartbeat), time of day, conversation length
- Injected into system prompt dynamically
- Drives OLED face expression via control WS message

---

## Dev Notes

**Whisper model choice:** `base` on CPU with int8 quantization via `faster-whisper`. Do not use `small` or above — latency becomes unacceptable on i5 without GPU.

**Ollama model choice:** `llama3.2:1b` not `3b`. 1B is fast enough for 1–3 sentence replies. 3B adds ~1s latency with no meaningful quality gain for BMO's use case.

**Audio normalisation is not optional.** Piper and XTTS output at different sample rates. The Pico's I2S DAC expects exactly 16kHz, 16-bit, mono. Always normalise before sending.

**PostgreSQL volume:** Mount at `/var/lib/postgresql` (not `/var/lib/postgresql/data`) for Postgres 18+ compatibility. The image creates a versioned subdirectory itself.