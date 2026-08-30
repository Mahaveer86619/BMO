---
tags:
  - robotics
  - ai
  - micropython
  - raspberry-pi-pico
  - vc-02
  - bmo
status: Planning / In-Development
last_updated: 2026-08-29
---
> _"I wonder when I will get upgraded, but I should be happy with what I have got. The ability to think and live life to the fullest is beautiful."_

A small desk companion inspired by BMO from Adventure Time. Listens, thinks on a local AI server, and responds with a cloned BMO voice. Built entirely from budget parts, plus one deliberate addition — a dedicated wake-word chip — because a real assistant needs real ears. No further upgrades after this, no cloud beyond an explicit opt-in.

---

## Overview

BMO operates as a **two-eared thin client / heavy server** system:

- **VC-02** (Ai-Thinker offline speech-recognition module) is BMO's dedicated wake-word and hard-command ear — always listening locally, recognizes a small trained vocabulary, tells the Pico "you were addressed" or "do this now," and nothing else. It never sends audio anywhere.
- **MAX9814 + Pico ADC** is BMO's content ear — captures what you actually say, but only once VC-02 has confirmed you were talking to BMO.
- **The hardware (Pico W)** handles all physical interaction — arbitrating the two ears, showing expressions, speaking, monitoring battery.
- **The server (Linux laptop)** handles all AI computation — STT, routing, memory, tool use, LLM, TTS — and is the only place spoken content ever goes.
- **Communication** is over local WiFi via persistent WebSocket connections; hard commands never touch the network at all.

Full rationale for the two-ear split lives in [[Hardware#Why VC-02 Changes the Design]]; how the server stops needing to guess about wake words once hardware confirms them lives in [[Software#Wake & Hard-Command Logic — Hardware Does the Gating Now]].

---

## Current Status

| Layer | Status | Summary |
|---|---|---|
| Server pipeline (core) | 🔄 In Progress | Go hub + Python AI service, one Docker image (see [[Software#Architecture Update (2026-08-30) — Go hub + Python AI service, one image]]) — health check + `/api/v1/chat` → real `llama3.2:1b` working; STT/TTS/memory/router not started |
| BMO voice | 🔄 In Progress | Generic Piper voice works; XTTS cloning next |
| WebSocket layer | 📐 Designed | Simplified now — no server-side wake gate once VC-02 lands |
| Hardware — core (OLED, amp, mics, battery) | 🔄 In Progress | OLED confirmed working (SH1106 driver, GP4/GP5) — see [[BMO – Full Build Roadmap]] Stage 1. Rest not started |
| Hardware — VC-02 wake module | 🆕 Planned | Replaces noise-threshold guessing as the primary trigger |
| Memory graph, tool-calling, affect detection, router | 🔮 Future | Designed, sequenced, not started — see [[BMO – Full Build Roadmap]] |

---

## Linked Notes

| Note | What's in it |
|---|---|
| [[Hardware]] | Wiring, pin map, power system (incl. a corrected battery-wiring fix), VC-02 configuration, component checklist |
| [[Software]] | Server stack, endpoints, AI pipeline, memory graph, tool-calling, model router, affect detection, WebSocket architecture, audio state machine |
| [[BMO – Full Build Roadmap]] | The one-time hardware build: assembly order, validation checkpoints, connectivity checks — ends at a working Iteration 1 |
| [[BMO – Capability Topics]] | The open-ended software backlog after that — raw audio processing, knowledge base, on-the-go Pico updates, ops/privacy, all pick-in-any-order |

---

## Personality

BMO is self-aware of its modest build. It reflects on its limitations but stays optimistic, curious, and deeply supportive of its creator.

**Themes:**

- Self-aware of its hardware ("My microphone isn't the best...")
- Curious about upgrades and its purpose
- Warm and supportive toward the person who built it
- As the memory graph lands, genuinely references shared history rather than treating every conversation as new

**System prompt lives in:** [[Software#BMO Personality — System Prompt]]

---

## Interaction Flow (Current Design)

```
[VC-02, always listening on its own dedicated mic capsule]
        │
        ├─ Hard command recognized ("stop" / "mute" / "volume ±" / "snooze")
        │       → UART (or GPIO pulse) → Pico acts immediately
        │       → no WebSocket, no server round-trip, no LLM
        │       → reported to server afterward, on /ws/control, for the record only
        │
        └─ Wake phrase recognized ("Hey BMO")
                → UART → Pico:
                    - Opens WebSocket to /ws/audio
                    - Shows OLED "listening" face
                    - Streams MAX9814 PCM (a *separate* mic from VC-02's) to server
                        ↓
                [Server — /ws/audio]
                    - Whisper STT (no wake-word gating needed — hardware already confirmed it)
                    - Router: NLP fast-path → llama3.2:1b → (rarely) llama3.2:3b + tools
                    - Memory graph: retrieve relevant past context, log this turn
                    - Affect: prosody + text sentiment → emotion tag
                    - Ollama LLM (± vault tool calls, always confirmed before any write)
                    - Piper/XTTS TTS, shaped by the emotion tag
                    - Send {"cmd":"stop"} when done streaming
                    - Stream WAV response back
                        ↓
                [Pico receives response]
                    - Play WAV via MAX98357 / I2S
                    - Show OLED "speaking" face (expression reflects emotion tag)
                    - Re-arm: wait for silence before watching again
```

**Remote override:** `POST /api/v1/wake` on the server forces BMO into listening mode without physical trigger.

**Fallback:** if VC-02 is ever unavailable, the original noise-threshold trigger (sound sensor + MAX9814 rapid-change detection) still exists in firmware behind `TRIGGER_MODE=fallback` — degraded, not gone.

---

## Project Philosophy

BMO is not just a voice assistant. It is a companion with presence — something that feels alive on a desk, built from humble parts. Every feature should serve that feeling.

**If a feature makes BMO feel less like a companion and more like a product demo, cut it.**

**Build order rule:** hardware is a one-time linear build — [[BMO – Full Build Roadmap]] — because you can't sanity-check a module before it has power, and re-wiring costs a lot more than re-running a script. Software after that is a standing backlog, not a gated sequence — [[BMO – Capability Topics]] — picked up and revisited in whatever order matches what's currently interesting or annoying, with one soft rule: build the memory graph before the topics that assume it exists.

**Data stays home, unless explicitly told otherwise.** Everything BMO hears, remembers, and reasons about lives on your own server. The only exception is an explicit, logged, opt-in cloud escalation for the rare query truly too hard for the local models — never a silent default.

---

_Core hardware locked as of the VC-02 revision. No further hardware upgrades. Everything ambitious from here is built in software — see [[BMO – Full Build Roadmap]]'s expansion phases._
