---
tags:
  - robotics
  - ai
  - micropython
  - raspberry-pi-pico
  - bmo
status: Planning / In-Development
---
> _"I wonder when I will get upgraded, but I should be happy with what I have got. The ability to think and live life to the fullest is beautiful."_

A small desk companion inspired by BMO from Adventure Time. Listens, thinks on a local AI server, and responds with a cloned BMO voice. Built entirely from budget parts — no upgrades, no cloud.

---

## Overview

BMO operates as a **thin client / heavy server** system:

- **The hardware (Pico W)** handles all physical interaction — listening, showing expressions, speaking, monitoring battery.
- **The server (Linux laptop)** handles all AI computation — STT, LLM, TTS.
- **Communication** is over local WiFi via persistent WebSocket connections.

---

## Current Status

|Layer|Status|Summary|
|---|---|---|
|Server pipeline|✅ Complete|Full WAV→WAV pipeline working, Dockerised, Postman tested|
|BMO voice|🔄 In Progress|Generic Piper voice works; XTTS cloning next|
|WebSocket layer|📐 Designed|Architecture finalised, not yet implemented|
|Hardware|⏳ Not started|All components in hand except slide switch|

---

## Linked Notes

|Note|What's in it|
|---|---|
|[[Hardware]]|Wiring, pin map, power system, component checklist, step-by-step build guide|
|[[Software]]|Server stack, endpoints, AI pipeline, WebSocket architecture, audio state machine|
|[[BMO – Full Build Roadmap]]|All phases, per-task checklists, progress tracking|

---

## Personality

BMO is self-aware of its modest build. It reflects on its limitations but stays optimistic, curious, and deeply supportive of its creator.

**Themes:**

- Self-aware of its hardware ("My microphone isn't the best...")
- Curious about upgrades and its purpose
- Warm and supportive toward the person who built it

**System prompt lives in:** [[Software#BMO Personality — System Prompt]]

---

## Interaction Flow (Current Design)

```
[Noise level crosses NOISE_THRESHOLD]
        ↓
[Pico W — rapid change detected (silent→loud)]
  - Open WebSocket to /ws/audio
  - Show OLED "listening" face
  - Stream raw PCM chunks to server
        ↓
[Server — /ws/audio]
  - Receive audio stream
  - Check first chunk for wake word "Lumi" via Whisper
  - If no wake word → send {"cmd":"stop"} → Pico goes idle
  - If wake word found → run full pipeline
  - Whisper STT → NLP intent → Ollama LLM → Piper/XTTS TTS
  - Send {"cmd":"stop"} when done streaming
  - Stream WAV response back
        ↓
[Pico W receives response]
  - Play WAV via MAX98357 / I2S
  - Show OLED "speaking" face
  - Re-arm: wait for silence before watching again
```

**Remote override:** `POST /api/v1/wake` on the server forces BMO into listening mode without physical trigger.

---

## Project Philosophy

BMO is not just a voice assistant. It is a companion with presence — something that feels alive on a desk, built from humble parts. Every feature should serve that feeling.

**If a feature makes BMO feel less like a companion and more like a product demo, cut it.**

**Build order rule:** Never add a new feature until the previous phase is stable.

---

_Hardware locked. No upgrades. Build with what you have._