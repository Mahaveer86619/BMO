---
status: In Development
hardware: Raspberry Pi Pico W + Ai-Thinker VC-02-Kit (fixed — no further upgrades)
server: Linux Laptop (i5, 16GB RAM)
architecture: Thin Client (Pico W + VC-02) + Local AI Server (Laptop)
project: "[[Custom BMO – Desk AI Bot]]"
tags:
  - bmo
  - roadmap
  - vc-02
last_updated: 2026-08-29
---
---

> _"I wonder when I will get upgraded, but I should be happy with what I have got. The ability to think and live life to the fullest is beautiful."_

---

## Build Model

This is **one continuous build, not a sequence of gated phases.** There is no "don't touch software until hardware Phase N is marked done" — the two happen together, checked as you go.

- **Stage 1 — Hardware Assembly & Validation.** Build all of it, in a sensible wiring order, and prove each module works in isolation the moment it's wired — the order is linear because that's just sound electronics practice (you can't sanity-check the amp before it has power), not because later modules are locked behind earlier ones as "features."
- **Stage 2 — Connectivity Checkpoints.** Interleaved with Stage 1, not after it. As soon as a module makes some new kind of network behavior testable, spin up the server (it already fully exists — see [[Software]]) and check that data actually moves the way it's supposed to.
- **Stage 3 — Software Iteration.** Once Stage 1 + Stage 2 produce one working end-to-end loop, that's **Iteration 1** — a real, working BMO. Everything past that point is the open backlog in [[BMO – Capability Topics]]: pick topics in any order, revisit them repeatedly, no gate, no "done forever."

**Bare minimum for Iteration 1**, in full: all hardware from the checklist below wired and validated, VC-02 configured for a wake phrase only (no hard commands yet), and the software exactly as already built/speced — Whisper → NLP fast-path → `llama3.2:1b` → Piper, over `/ws/audio` + `/ws/control`. XTTS cloning, hard commands, memory, tools, everything in the Topics doc — none of it is required to call this done.

---

## Stage 1 — Hardware Assembly & Validation

Wire and test one component at a time, in this order. Full wiring diagrams, pin maps, and test snippets for every step live in [[Hardware]] — this is the build-order checklist; go there for the how.

- [x] **OLED** — wire I2C (GP4/GP5), run the `i2c.scan()` + "BMO online" test ([[Hardware#Step 1 — OLED Display]]) — confirmed working 2026-08-30, with the sh1106 driver (see notes/oled_bringup_final.html)
- [x] **WiFi** — flash MicroPython, connect via `network` module, confirm `wlan.isconnected()` — confirmed working 2026-08-30
- [ ] **MAX98357 amp** — wire I2S (GP10/11/12) to VSYS, run the 440Hz tone test ([[Hardware#Step 5 — MAX98357 I2S Amplifier]])
- [ ] **Sound sensor (fallback trigger)** — wire AO to GP28 (ADC2 — GP26 is the mic's), run the trigger-print test ([[Hardware#Step 2 — Sound Sensor (Fallback Trigger)]]). Deprioritized 2026-08-30 — even with the AO fix it's an inherently unreliable trigger (ambient-noise-dependent, no real "was this speech" intelligence), which is exactly why VC-02 exists. Fine to leave unwired for now; it's a fallback, not a dependency for anything else.
- [ ] **MAX9814 (content mic)** — wire to GP26/ADC0, run the ADC read test, calibrate `NOISE_THRESHOLD` ([[Hardware#Step 3 — MAX9814 Microphone (Content Capture)]])
- [ ] **VC-02** — configure wake phrase via `voice.ai-thinker.com` *before* wiring, then wire VCC→VSYS/GND/TX1→GP1/RX1→GP0, run the UART echo test ([[Hardware#Step 4 — VC-02 Wake & Hard-Command Module (NEW)]])
- [ ] **Battery pack** — wire the two 18650s in **parallel** (not series — see [[Hardware#⚠️ Power Planning — Read Before Wiring Anything]]), wire the divider to GP27, confirm 134N3P output reads 4.9–5.1V on a multimeter *before* connecting the Pico
- [ ] **Full power-on smoke test** — everything wired, running off the battery pack, nothing overheats or browns out under a full conversation load

---

## Stage 2 — Connectivity Checkpoints

Don't wait until Stage 1 is entirely finished to touch the server — check each new capability the moment it's wireable. The server side of every checkpoint below already exists; see [[Software]] for the endpoint/WebSocket details.

- [x] **Checkpoint A — reachability.** After OLED + WiFi: Pico hits `GET /health` or `/api/v1/status` and gets a response. Proves nothing more than "Pico can talk to the laptop" — do this before debugging anything more complex. Confirmed 2026-08-30 — went further than a one-shot check: continuous polling every 5s with both server and Pico uptime shown live on the OLED (firmware/tests/09_health_display.py).
- [ ] **Checkpoint B — downstream audio.** After the amp: request a WAV from `/api/v1/talk` (or a stubbed `/ws/audio` reply) and play it. Proves the response path — server → Pico → speaker — independent of the mic.
- [ ] **Checkpoint C — upstream audio.** After MAX9814: stream real PCM up over `/ws/audio`, save it server-side to a file, and listen back. Proves the capture path — Pico → server — independent of VC-02 or the LLM. If it sounds garbled, fix it here before adding VC-02 into the loop.
- [ ] **Checkpoint D — full loop.** After VC-02: say the wake phrase, confirm the stream opens, confirm the full pipeline runs (Whisper → NLP/Ollama → Piper), confirm the response plays and the OLED cycles through all states correctly. **This checkpoint is Iteration 1, complete.**
- [ ] **Checkpoint E — battery telemetry.** After the battery pack: confirm voltage/percentage reports correctly over `/ws/control`'s heartbeat.

If a checkpoint fails, the fix belongs to whichever side is simplest to isolate first — usually the freshest hardware step, but don't assume; Checkpoint C existing independently of D is specifically there so a bad wake trigger and a bad audio stream never get debugged as one tangled problem.

---

## Stage 3 — Software Iteration

Everything from here is the open backlog in **[[BMO – Capability Topics]]**. No fixed order beyond one soft recommendation: build the Personal Memory Graph topic before the ones that assume it (vault tools, personalization) — everything else can be picked up in whatever order matches what's currently annoying to not have.

Quick pointer into that doc's groups:

| Group | Covers |
|---|---|
| A — Wake, Trigger & Physical I/O | Hard commands, fallback trigger tuning, battery UX — small refinements on top of Stage 1 |
| B — Raw Audio Input Processing | Affect/mood from voice, speaker ID, ambient transcription, wake-confidence logging |
| C — Knowledge Base Expansion | Memory graph, vault tool-calling, model router, personalization loop |
| D — On-The-Go Pico Updates | Push config/faces/filler-phrases to the Pico without re-flashing over USB; optional true OTA |
| E — Ops, Privacy & Multi-Device | `BMO_MODE`, the data-boundary rule, eventual second physical BMO |

---

## Key Code Reference

Wiring-level test snippets (I2C/OLED, MAX9814, MAX98357, VC-02 UART echo, battery divider) live in [[Hardware]]. Firmware state machine and trigger constants live in [[Software#Pico W Firmware State Machine]]. Kept here: the two snippets that don't belong to a single component.

### WiFi Connection

```python
import network, time

def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        time.sleep(0.5)
    print("Connected:", wlan.ifconfig())
```

### I2S Audio Playback

```python
from machine import I2S, Pin

audio_out = I2S(
    0,
    sck=Pin(10), ws=Pin(11), sd=Pin(12),
    mode=I2S.TX,
    bits=16,
    format=I2S.MONO,
    rate=16000,
    ibuf=4096
)

def play_audio(wav_bytes):
    # Skip 44-byte WAV header, play raw PCM
    audio_out.write(wav_bytes[44:])
```

---

_Last updated: 2026-08-29_ _Core hardware set (Pico W, OLED, MAX98357, MAX9814, VC-02) is locked as of this revision — Stage 1 is a one-time build. Everything past Checkpoint D is open-ended software work; see [[BMO – Capability Topics]]._
