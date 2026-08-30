---
project: "[[Custom BMO – Desk AI Bot]]"
tags:
  - bmo
  - roadmap
  - topics
last_updated: 2026-08-29
---
> This is not a phased roadmap. [[BMO – Full Build Roadmap]] covers the one-time linear hardware build; everything here is the **open-ended software backlog** that starts once that build produces a working loop. Pick topics in whatever order interests you, revisit them repeatedly, and don't treat any of them as "done forever" — this list is meant to be edited as ideas change.

Each topic states: what it is, how it actually works, what it depends on, and whether it's part of the bare-minimum first iteration.

---

## Bare Minimum — Iteration 1

Before any topic below is relevant, this is the whole target for the first working version:

**Hardware (all of it, wired and validated per [[BMO – Full Build Roadmap]]):** Pico W, OLED, MAX9814 (content mic), sound sensor (fallback trigger), VC-02 **configured for a wake phrase only** — no hard commands yet, that's an optional refinement — MAX98357 amp, battery pack wired in parallel.

**Software (all of it already speced in [[Software]], nothing new):** Whisper STT → NLP fast-path → Ollama `llama3.2:1b` → Piper TTS, over `/ws/audio` + `/ws/control`, Pico firmware cycling IDLE → LISTENING → THINKING → SPEAKING → REARMING.

That's a genuinely working desk assistant. XTTS cloning, hard commands, and every topic below are explicitly *not* required to call it done.

---

## Topic Group A — Wake, Trigger & Physical I/O

Mostly hardware-anchored, mostly already covered in [[Hardware]] and [[Software]]. Listed here for completeness of the map.

### A1. Wake & Hard-Command Detection (VC-02)
Wake phrase is Iteration 1. Hard commands (`stop`, `mute`, `volume ±`, `snooze`) are a cheap, high-value add-on once the base loop works — train them into VC-02's existing config, add the `HARD_COMMAND` firmware state. See [[Software#Wake & Hard-Command Logic — Hardware Does the Gating Now]].

### A2. Fallback Trigger
Sound sensor + noise-threshold heuristic, dormant behind `TRIGGER_MODE=fallback`. Build and calibrate it alongside VC-02 (it's nearly free), but it only matters if VC-02 misbehaves.

### A3. Battery Awareness
Voltage read, OLED percentage, low-battery face and line. Straightforward once the divider is wired — see [[Hardware#Step 6 — Battery Voltage Divider]].

---

## Topic Group B — Raw Audio Input Processing

Everything here works on audio you're *already* capturing for STT — no new mic, no new wiring. The idea: don't throw away the raw PCM after Whisper is done with it.

### B1. Affect / Prosody Detection
Extract pitch (F0), energy/RMS, and speaking rate from the same buffer Whisper already transcribed, using `librosa` — no extra model needed for a first pass. Fuse with basic text sentiment on the transcript into one of a small fixed set (neutral / stressed / upbeat / tired). Feed that tag into XTTS's `speed`/`temperature` and into which OLED expression plays during SPEAKING. Full design: [[Software#Affect Detection]].

**Why it matters:** replaces "BMO's mood is just battery % and time of day" with "BMO's mood reflects how you actually sound" — the single cheapest upgrade to how alive it feels.

### B2. Speaker Identification
A lightweight voiceprint model on MAX9814 capture to tell you apart from anyone else talking to BMO. Personalizes memory retrieval and tone per speaker. Not worth building until there's routinely more than one voice in the room — it's an enhancement to memory, not a prerequisite for it.

### B3. Ambient Transcription (Desk Mode)
Continuous background transcription, not just wake-triggered turns — a private, searchable log of desk life. **Deliberately the last topic to build**, even though it's technically simple, because it's the biggest privacy surface in the project and directly conflicts with the battery-conscious design if done carelessly:

- Hard-gated to `BMO_MODE=desk` (assumes USB/mains power) — never runs in `portable` mode, no override.
- Stored in a table separate from real wake-triggered conversations — BMO should never treat something merely overheard the same as something said *to* it.
- Explicit retention window (e.g. rolling 30 days), auto-purged.
- A spoken redaction command ("BMO, forget the last five minutes") that hard-deletes rows, not just hides them.

Full design: [[Software#Ambient Transcription (Desk Mode Only)]].

### B4. Wake-Confidence Logging
Since Whisper runs on every accepted stream anyway, it's nearly free to log whether the transcribed text actually starts with the wake phrase — a running signal for whether VC-02's trained sensitivity needs retuning in the Ai-Thinker platform over time. Non-blocking, logging-only, never gates a response.

---

## Topic Group C — Knowledge Base Expansion

The highest-leverage group. Do C1 before the others in this group — everything else compounds on it existing.

### C1. Personal Memory Graph
Postgres + `pgvector` on the same database already used for conversation persistence. Structured tables (`conversations`, `turns`, `entities`, `mentions`) for relational facts, vector embeddings on `turns.text` for semantic recall. Before every LLM call: embed the current utterance, pull top-k similar past turns plus any known entities mentioned, inject a short "relevant context" block. After every turn: store it, extract entities (heuristics first, LLM fallback), embed it. Full design: [[Software#Personal Memory Graph]].

**Why first:** this is the difference between "stateless chatbot" and "remembers you" — and both C2 and B2 assume it exists.

### C2. Vault Tool-Calling
BMO reads and, carefully, writes this Obsidian vault by voice. A small explicit tool set — `read_note`, `list_todos`, `git_log_summary` (read-only, build these first), `append_note`, `create_note` (write — always requires a spoken confirmation before executing, always logged). Runs on a step-up model (`llama3.2:3b`) since the 1B model isn't reliable enough for structured tool calls. Full design: [[Software#Tool-Calling & Vault Integration]].

### C3. Model Router
Three tiers, cheapest first: NLP fast-path (free) → `llama3.2:1b` (default, almost everything) → `llama3.2:3b` + tools (only when C2 is needed or the query is multi-step). A fourth tier — cloud escalation — exists only as an explicit, logged, opt-in last resort; never a silent default. Full design: [[Software#Model Router]].

### C4. Personalization Loop
Periodic local LoRA fine-tune on accumulated transcripts and this vault's own writing, so BMO's phrasing drifts toward actually sounding like it knows you. Meaningfully more infrastructure (a training pipeline, eval-before-promote so a bad fine-tune never ships) for a marginal gain once C1 already exists. Lowest priority in this group — skip indefinitely without regret if the memory graph alone feels like enough.

---

## Topic Group D — On-The-Go Pico Updates

New ground not covered in the original design: right now, changing anything on the Pico — a new OLED face, a tuned threshold, a new filler phrase — means physically re-flashing over USB. Once the base loop is stable, most of that friction is removable, since the Pico already has a permanent WebSocket open to the server (`/ws/control`).

### D1. Live Config Updates
Move tunable constants (`NOISE_THRESHOLD`, `REARM_SILENCE_MS`, `TRIGGER_MODE`, hard-command mappings) out of hardcoded firmware and into a small config the Pico pulls from the server on boot, or receives as a control-channel message (`{"cmd":"config_update", ...}`). Tune from the server side, push a message, done — no cable, no re-flash, no reboot-and-hope.

### D2. Live Filler-Phrase / Audio Asset Updates
Filler phrases (played during THINKING) currently live as fixed files on the Pico. Instead, let the server host the current set and version them; Pico checks a version number on boot or on a control-channel ping, fetches anything new over HTTP, caches to flash. Add or rotate filler lines from the server without touching the device.

### D3. Live Face/Animation Updates
Same pattern for OLED expressions: server hosts a small manifest of face bitmaps/animation frames, Pico diffs against what it has cached and pulls anything new. Lets you iterate on BMO's expressiveness — a new "curious tilt" animation, a new low-battery face — without ever opening a USB session again.

### D4. True OTA Firmware Updates *(optional, higher risk — build last in this group)*
Pushing actual replacement `.py` files to the Pico over WiFi and rebooting into them. Genuinely useful once the above three are boring and reliable, but a bad push without a safety net can brick the device's ability to ever accept another OTA push. If you build this: always keep a last-known-good copy in a separate flash location, verify the new code boots and reconnects successfully before overwriting the fallback, and never make OTA the only way to recover a broken Pico — USB re-flash must always still work as the ultimate escape hatch.

---

## Topic Group E — Ops, Privacy & Multi-Device

Overarching concerns and the furthest-out idea, not really an "add a feature" topic in the same sense as the groups above.

### E1. `BMO_MODE` (desk / portable)
A single shared flag between firmware and server. Gates B3 (ambient transcription) and reflects the runtime budget established in [[Hardware#Current budget]]. Keep the two in sync — don't let the server assume desk mode while the Pico is actually on battery.

### E2. Data Boundary
Stated once, meant to be checked against every future idea before it's built: everything BMO hears, remembers, and reasons about lives on your own server. The only sanctioned exception is C3's explicit, logged, opt-in cloud escalation. Any future "cloud feature" idea gets weighed against this line, not assumed compatible with it.

### E3. Multi-Satellite Expansion *(far future)*
A second Pico + VC-02 + mic/speaker set, same server, same memory graph, with server-side session/device identity so two physical bodies don't cross-talk in one conversation. Only worth starting once a single unit has been genuinely reliable for a long stretch — this is the one topic that's explicitly gated behind "the rest of this list is boring now," not a matter of picking it up whenever.
