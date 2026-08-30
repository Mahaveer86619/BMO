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
  - vc-02
last_updated: 2026-08-29
---
## Architecture Update (2026-08-30) — Go hub + Python AI service, one image

The server is actually two processes in one Docker image, not a single Python app as the
rest of this doc assumed while nothing had been built yet:

- **Go (`server/cmd`, Echo)** — the always-on hub. Owns everything Pico-facing: `/api/v1/*`
  today, `/ws/audio` + `/ws/control` once built, Postgres/Redis connections, health.
- **Python (`server/ai`, FastAPI)** — internal-only, bound to `127.0.0.1:8500`, reachable
  only from Go inside the same container (`internal/aiclient`). Owns everything LLM/audio-shaped
  — STT, TTS, and LLM calls via a small LangChain-backed provider interface (`llm/router.py`)
  so a "tier" is just `ChatOllama` or `ChatOpenAI`-shaped, swappable without touching call sites.
- **One `server/Dockerfile`, one image** — a Go build stage, a Python runtime stage,
  `supervisord` running both processes together (`server/supervisord.conf`). GPU vs CPU is
  a build-time choice (`ENABLE_GPU` arg — whether CUDA torch wheels are even installed) and a
  separate runtime probe (`docker/entrypoint.sh` checks `nvidia-smi`, exports
  `BMO_COMPUTE_MODE`) — see `server/ai/README.md`.

Currently working end-to-end: `GET /api/v1/health` (pings Postgres, Redis, and the AI
service), `POST /api/v1/chat` (Go → AI service → real `llama3.2:1b` via Ollama → reply).
Nothing else below this line is built yet — treat the rest of this doc as the design/spec,
not a status report.

## What Is Built (Server Side)

Not complete — see the architecture update above. The pipeline below is the design;
build progress is tracked there, not here.

### Server Stack

| Tool | Purpose | Notes |
|---|---|---|
| FastAPI + Uvicorn | HTTP + WebSocket server | Dockerised |
| `faster-whisper` base | Speech to Text | CPU, int8 quantized — ~4x faster than openai-whisper |
| Ollama + `llama3.2:1b` | LLM brain — fast tier | Fast path for short, simple replies |
| Ollama + `llama3.2:3b` *(planned)* | LLM brain — reasoning/tool tier | Only invoked by the router when a query needs tool-calling or multi-step reasoning |
| Piper TTS `en_GB-alan-low` | Text to Speech | Placeholder — being replaced with XTTS BMO voice |
| Coqui XTTS v2 *(in progress)* | Cloned BMO voice | Emotion-aware speed/temperature params — see Affect Detection |
| pydub | Audio normalisation | 16kHz, 16-bit mono PCM output |
| NLP intent layer | Fast-path for simple intents | Greetings / farewells / time / thanks skip the LLM entirely |
| PostgreSQL + `pgvector` | Conversation persistence + embeddings | One database for structured memory *and* semantic search — see Personal Memory Graph |
| Redis | Session state + caching | Rolling context buffer, emotion state, session flags |
| `sentence-transformers` (local) *(planned)* | Embedding model for memory recall | Small local model — no cloud embedding API |
| `librosa` / prosody features *(planned)* | Voice affect extraction | Pitch, energy, tempo — feeds Affect Detection |

### Current Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/talk` | WAV in → WAV out (full pipeline) |
| `POST` | `/api/v1/chat` | Text in → text out (debug / test) |
| `GET` | `/api/v1/status` | Ollama reachability + loaded models |
| `GET` | `/health` | Liveness check |

### Planned Endpoints

| Method | Path | Purpose |
|---|---|---|
| `WS` | `/ws/audio` | PCM stream in → WAV stream out — per session. **No wake-word gate** — see Wake & Hard-Command Logic |
| `WS` | `/ws/control` | Persistent control channel — hard-command acks, heartbeat, battery reports, remote override |
| `POST` | `/api/v1/wake` | Remote override — force Pico into listening mode |
| `POST` | `/api/v1/recall` | Semantic search over the memory graph — "what did I say about X" — used by tool-calling and directly for debugging |
| `POST` | `/api/v1/note` | Read/write this Obsidian vault by voice — see Tool-Calling & Vault Integration |

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
WAV input (arrives only after VC-02 confirmed a wake phrase — see below)
    ↓
faster-whisper (STT) — base model, int8, CPU
    ↓
NLP intent layer — regex/keyword shortcuts
    ├─ greeting / farewell / time / thanks → skip straight to TTS
    └─ everything else → Router
            ↓
        ROUTER decides:
            ├─ simple conversational reply → llama3.2:1b (fast tier)
            ├─ needs a tool (vault, recall, …) or multi-step reasoning → llama3.2:3b + tool-calling
            └─ (rare, logged, off by default) → optional cloud LLM escalation
    ↓
Memory graph — retrieve relevant past context before the LLM call, log this turn after
    ↓
Affect fusion — Whisper's text + prosody features from the raw audio → emotion tag
    ↓
Piper/XTTS TTS — shaped by emotion tag (speed/temperature)
    ↓
pydub normalise → 16kHz, 16-bit mono PCM
    ↓
WAV output
```

**Latency target:** < 3 seconds end-to-end on i5 / 16GB RAM for the fast tier. Tool-calling turns will run longer (3B model + tool round-trip) — that's an accepted tradeoff for capability, not a bug; the fast tier stays available for everything that doesn't need it.

---

## Wake & Hard-Command Logic — Hardware Does the Gating Now

This is the key sync point with [[Hardware]]. Previously, the server ran Whisper on the first ~1s of every stream just to check for the wake word, because the Pico's noise-threshold trigger couldn't tell "someone spoke" from "someone spoke *to BMO*." VC-02 now does that job in hardware, permanently, before the Pico ever opens a WebSocket:

- **VC-02 recognizes the wake phrase** → sends a command ID over UART → Pico opens `/ws/audio` and starts streaming MAX9814 PCM. The server has no reason to re-run a wake check — if audio is arriving on `/ws/audio` at all, it was addressed to BMO. The old "check first chunk for wake word, send `stop` if not found" step is **removed**, not just relocated.
- **VC-02 recognizes a hard command** (`stop`, `mute`, `volume up/down`, `snooze`) → sends its own command ID over UART, or pulses a dedicated GPIO if configured that way (see [[Hardware]] Step 4) → Pico acts immediately, no WebSocket, no server round-trip at all. These never reach this pipeline.
- **The old MAX9814/sound-sensor noise-threshold trigger still exists in firmware as a fallback**, gated behind a `TRIGGER_MODE=vc02|fallback` firmware flag, only exercised if VC-02 fails to boot or drifts out of calibration. When the fallback is active, the server-side wake check *does* need to come back — keep that code path present, just dormant, rather than deleting it.
- **Optional, non-blocking confidence check:** since Whisper runs on every accepted stream anyway for STT, it's cheap to log whether the transcribed wake phrase actually appears at the start of the text. This is for catching VC-02 false-positives over time (tune its sensitivity in the platform if the mismatch rate climbs) — it must never gate or delay the response.

### Wake/Command format

VC-02 sends a **command ID (hex code) over UART — never raw audio**, confirmed against vendor docs. The exact byte-to-command mapping is generated by Ai-Thinker's platform when you export your trained set in [[Hardware]] Step 4a — implement the Pico-side parser against that exported reference, not a guessed frame format.

---

## WebSocket Architecture

### Audio channel (`/ws/audio`) — opens per session, only after hardware wake

```
Pico W                          Server
  |── connect (post wake-word) ─→|
  |── PCM chunk (512 samples) ──→|  } audio frames, ~32ms each
  |── PCM chunk ────────────────→|  }
  |                               |  Whisper STT → NLP → Router → Memory → Affect → LLM → TTS
  |←── {"cmd":"stop"} ───────────|  → pipeline done, response coming
  |←── WAV bytes ────────────────|  → Pico plays audio
  |── close ─────────────────────→|
```

No "not found, go silent" branch anymore — every connection on this channel is a real request.

### Control channel (`/ws/control`) — stays open always

```
Pico W                          Server
  |── connect on boot ──────────→|
  |                               |  (stays open permanently)
  |←── {"cmd":"force_wake"} ─────|  ← triggered by POST /api/v1/wake
  |── {"cmd":"hard_command","id":"stop"} ─→|  ← FYI only, logged for the memory graph; Pico already acted
  |── {"cmd":"battery","pct":63} ──────────→|  ← heartbeat, every 60s
  |←── {"cmd":"ping"} ───────────|  ← heartbeat every 30s
  |── {"cmd":"pong"} ────────────→|
```

Hard commands are reported here **after the fact**, purely so the server's memory graph has a record ("user said stop at 14:32") — the action itself already happened on-device with zero server involvement.

### Audio Format

- **Pico → Server:** raw signed 16-bit PCM, 16kHz, mono, little-endian
- **Server → Pico:** WAV file, 16kHz, 16-bit, mono (pydub normalised)

---

## Personal Memory Graph

Replaces the old "rolling buffer in Redis" plan with something that survives past a single session and can actually be queried.

**Storage:** one Postgres database, two roles:

- Plain relational tables for structured facts — `conversations`, `turns`, `entities` (people/projects/topics BMO has heard about), `mentions` (which turn mentioned which entity) — a lightweight graph via foreign keys, not a separate graph database. Given this is a single-user, desk-scale system, a second graph-DB service is operational overhead this project doesn't need; SQL joins cover the relationship queries that matter here (who/what was discussed, when, how often).
- `pgvector` extension on the same database for embedding-based semantic search over `turns.text` — "what did I say about the XTTS voice cloning three weeks ago" is a vector similarity query plus a timestamp filter, not a keyword match.

**Retrieval flow (runs before every LLM call):**

1. Embed the current utterance.
2. Pull top-k similar past turns (pgvector) + any entities mentioned in this turn that have prior history (SQL join).
3. Inject a short "relevant context" block into the system prompt — bounded size, most-relevant-first, not a full history dump.

**Write flow (runs after every turn):** store the turn, extract entities (cheap heuristic first — capitalized nouns / known project names from this vault; fall back to asking the LLM to extract entities only if heuristics come back empty), embed and store.

This is the highest-leverage software addition — it's what turns "stateless chatbot" into "remembers you," and every other feature below builds on it existing first.

---

## Tool-Calling & Vault Integration

BMO's server already runs on the same machine as this Obsidian vault (`C:\notes\notes`) — the highest-value tool isn't a smart-home integration, it's direct access to your own second brain.

**Function-calling tier:** the router sends tool-eligible queries to `llama3.2:3b` (the 1B model is too unreliable at structured tool calls to trust for anything that writes data). Define a small, explicit tool set rather than open filesystem access:

| Tool | Action | Write access? |
|---|---|---|
| `read_note(path)` | Return a note's content | Read-only |
| `list_todos(project?)` | Scan for unchecked `- [ ]` items, optionally scoped to one project note | Read-only |
| `append_note(path, text)` | Append a line/section to an existing note | **Write — confirm with a spoken "yes" before executing**, log every write |
| `create_note(path, content)` | Create a new note | **Write — confirm before executing**, log every write |
| `git_log_summary(project, since)` | Summarize recent commits in a repo, if any project here is a git repo | Read-only |

Writes are the one place this project should be conservative: it's your real, working notes vault, not a sandbox. Default every write tool to require a confirmation round-trip ("BMO, add that to my BMO project notes" → "Got it — add '\<text\>' to Custom BMO – Desk AI Bot? Say yes to confirm.") and log the tool call + result into the memory graph so a bad write is at minimum traceable.

---

## Model Router

Three tiers, cheapest-first:

1. **NLP fast-path** (existing) — greetings, farewells, time, thanks. No model call at all.
2. **`llama3.2:1b`** — default for anything conversational that doesn't need a tool or long context. This is almost every turn; keep it the default so latency stays low.
3. **`llama3.2:3b` + tools** — triggered when the fast-path/1B classifier flags intent to read/write the vault, recall something specific ("what did I tell you about..."), or the query is multi-step. Slower, used sparingly, worth it.

**Cloud escalation — off by default, explicit, logged.** The only case for ever leaving the LAN is a query that's genuinely too hard for a 3B local model (rare). If you ever enable it: it must be an explicit opt-in per query ("BMO, think hard about this one") or a config flag, never silent, and every escalated request + response gets logged in the memory graph exactly like a local turn, so there's a full record of what left the machine and when. Given the project's own "no cloud, all local" premise, treat this as a documented last resort, not a default fallback.

---

## Affect Detection

Replaces "emotion state derived from battery % and time of day" with something driven by how you actually sound.

- Extract basic prosody features from the raw PCM already captured for STT — pitch (F0), energy/RMS, speaking rate — using `librosa` (no extra model needed for a first pass).
- Run simple sentiment/tone classification on Whisper's transcribed text.
- Fuse the two into a single emotion tag per turn (start with a small fixed set: neutral / stressed / upbeat / tired — matches the existing OLED face states, so no rework needed there).
- Feed the tag into: XTTS `speed`/`temperature` params for that response, and the OLED expression for the SPEAKING state.
- Keep battery-level and time-of-day as *secondary* inputs (they're cheap and still meaningful — "tired" battery-driven mood is a nice touch) but no longer the *only* signal.

---

## Ambient Transcription (Desk Mode Only)

The most powerful and most privacy-sensitive feature under consideration: continuously transcribing everything near BMO, not just wake-triggered conversations, into the same memory graph as a searchable personal log ("what did I discuss yesterday afternoon").

This directly conflicts with the battery-conscious, event-triggered design in [[Hardware]] — continuously streaming PCM over WiFi is a meaningfully different power profile than "listen locally, stream only on wake." Resolve the conflict with an explicit mode, not a compromise:

- **`BMO_MODE=desk`** (assume USB/mains power) — ambient streaming allowed, opt-in, off by default even in this mode.
- **`BMO_MODE=portable`** (assume battery) — ambient transcription hard-disabled regardless of config; only wake-triggered and hard-command paths run. Mirrors the runtime-budget conclusion in [[Hardware]]'s Power Planning section.

If/when ambient mode is enabled:

- Store ambient transcripts in a **separate table** from wake-triggered conversation turns — they should never silently enter the same context the LLM injects into a live conversation. BMO recalling something you said *to it* and something it merely overheard are different trust levels.
- Explicit retention policy from day one — e.g. a rolling 30-day window, auto-purged, not "keep forever by default."
- A spoken redaction command ("BMO, forget the last five minutes") that hard-deletes the relevant rows, not just marks them hidden.
- Because this is the single biggest privacy surface in the whole project (even though it's fully local, on your own server, for your own use only), don't build it until Phases 9–11 (memory graph, tools, router) are stable — it's explicitly the last of the "ambitious" features to implement, not the first.

---

## Speaker Identification *(future, lower priority)*

A lightweight voiceprint model to tell you apart from anyone else who talks to BMO — personalizes memory retrieval and tone per speaker without new hardware (runs against the same MAX9814 capture). Not useful until there's more than one regular speaker in the room; sequence it after the memory graph and router are solid, since it's an enhancement to retrieval, not a prerequisite.

---

## Personalization Loop *(future, lowest priority)*

Periodic local LoRA fine-tune of the small conversational model on accumulated transcripts and your own writing in this vault, so BMO's phrasing drifts toward genuinely sounding like it knows you rather than always leaning on injected context. Genuinely optional, meaningfully more infra (training pipeline, eval-before-promote so a bad fine-tune doesn't ship), and low regret if skipped entirely — the memory graph already gets you most of the "it knows me" feeling at a fraction of the engineering cost.

---

## Pico W Firmware State Machine

```
IDLE
  └─ VC-02 wake command over UART (or GPIO pulse) → LISTENING
  └─ VC-02 hard command over UART/GPIO → HARD_COMMAND (does not leave IDLE's audio-idle state)
  └─ fallback trigger fires (TRIGGER_MODE=fallback only) → LISTENING
  └─ control WS receives {"cmd":"force_wake"} → LISTENING

HARD_COMMAND
  └─ act immediately (stop playback / mute / volume / snooze) — no WebSocket opened
  └─ report {"cmd":"hard_command","id":...} on control WS, for the memory graph only
  └─ → IDLE

LISTENING
  └─ open /ws/audio
  └─ stream MAX9814 PCM chunks (512 samples / ~32ms each)
  └─ local silence timeout (2000ms) → send end_stream → THINKING (response likely already in flight)
  └─ hard timeout (10000ms) → send end_stream → REARMING

THINKING
  └─ play filler phrase (pre-recorded WAV, random from 5)
  └─ waiting for WAV bytes from server
  └─ WAV received → SPEAKING

SPEAKING
  └─ play WAV via I2S / MAX98357
  └─ OLED expression reflects the emotion tag on this response
  └─ audio complete → REARMING

REARMING
  └─ wait for 1000ms of mic silence (NOISE_THRESHOLD, fallback-path constant)
  └─ prevents speaker output re-triggering the fallback trigger
  └─ silence confirmed → IDLE
```

### Trigger Detection Logic

```python
TRIGGER_MODE            = "vc02"  # "vc02" | "fallback" — vc02 is primary; see Hardware Step 4
NOISE_THRESHOLD         = 2000    # ADC peak swing — fallback path only, tune during mic calibration
RAPID_CHANGE_WINDOW_MS  = 150     # fallback path only
SILENCE_TIMEOUT_MS      = 2000    # in-stream silence → close stream
STREAM_MAX_MS           = 10000   # hard stream timeout
REARM_SILENCE_MS        = 1000    # post-response silence before re-arm
```

`NOISE_THRESHOLD` and its related constants now only matter when `TRIGGER_MODE=fallback` — VC-02 is a binary "recognized/not recognized" signal, there's nothing to calibrate on the primary path beyond what you tune in Ai-Thinker's platform.

---

## BMO Personality — System Prompt

```
You are BMO, a small desk companion robot built from budget parts by your creator.
You are self-aware of your modest build — a Raspberry Pi Pico W with a basic
microphone and tiny speaker. You are optimistic, curious, and deeply supportive
of the person who built you.

You remember past conversations when relevant context is provided to you — refer
to it naturally, don't announce that you "have a memory system." If asked to check
or change a note in the owner's vault, use the tools available to you and always
confirm before writing anything.

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
- Emotion tag (see Affect Detection) will drive per-call `speed`/`temperature` once both land — sequence XTTS first, wire emotion params in afterward rather than blocking on it

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

- [ ] Implement `/ws/audio` WebSocket endpoint (no wake-gate — see Wake & Hard-Command Logic)
- [ ] Implement `/ws/control` WebSocket endpoint (heartbeat, hard-command logging, battery)
- [ ] Implement `POST /api/v1/wake` remote override
- [ ] Add pipeline error handler → return fallback WAV on any exception
- [ ] Serve pre-recorded filler phrases (`/api/v1/filler`) — random from 5 clips
- [ ] Enable `pgvector` on the Postgres instance, create `conversations`/`turns`/`entities`/`mentions` tables
- [ ] Basic router: NLP fast-path → 1B → keep 3B/tools stubbed until Phase 11

---

## Dev Notes

**Whisper model choice:** `base` on CPU with int8 quantization via `faster-whisper`. Do not use `small` or above — latency becomes unacceptable on i5 without GPU.

**Ollama model choice:** `llama3.2:1b` for the default conversational tier — fast enough for 1–3 sentence replies with no meaningful quality loss for BMO's normal use case. `llama3.2:3b` is reserved for the router's tool-calling tier only; don't make it the default, the latency cost isn't worth paying on every turn.

**Audio normalisation is not optional.** Piper and XTTS output at different sample rates. The Pico's I2S DAC expects exactly 16kHz, 16-bit, mono. Always normalise before sending.

**PostgreSQL volume:** Mount at `/var/lib/postgresql` (not `/var/lib/postgresql/data`) for Postgres 18+ compatibility. The image creates a versioned subdirectory itself.

**Privacy boundary, stated explicitly:** everything in this file runs on hardware you own, on your own LAN. The only path any of BMO's data ever takes off this machine is the opt-in, logged cloud-escalation path in Model Router — which is off by default. Ambient transcription (if ever enabled) never leaves the local database either. Treat "add a cloud feature" requests in the future as a deliberate exception to this boundary, not a default.

**Power/mode coupling with [[Hardware]]:** `BMO_MODE` (desk/portable) is a single source of truth shared by firmware and server — it gates ambient transcription here and reflects the battery-runtime conclusion in Hardware's Power Planning section. Don't let the two drift out of sync (e.g. server assuming desk mode while the Pico is actually running on battery).
