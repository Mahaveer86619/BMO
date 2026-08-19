---
status: In Development
hardware: Raspberry Pi Pico W (fixed — no upgrades)
server: Linux Laptop (i5, 16GB RAM)
architecture: Thin Client (Pico W) + Local AI Server (Laptop)
project: "[[Custom BMO – Desk AI Bot]]"
tags:
  - bmo
  - roadmap
last_updated: 2026-06-08
---
---

> _"I wonder when I will get upgraded, but I should be happy with what I have got. The ability to think and live life to the fullest is beautiful."_

---

## Progress Summary

|Phase|Status|Notes|
|---|---|---|
|1 — Server Foundation|✅ Complete|Full pipeline working, Dockerised, Postman tested|
|1.5 — BMO Voice|🔄 In Progress|Piper works; XTTS voice cloning in progress|
|1.6 — WebSocket Layer|📐 Designed|Architecture finalised, not yet implemented|
|2 — Pico W Basic Connection|⏳ Not started||
|3 — OLED Face|⏳ Not started||
|4 — Noise Trigger + Audio Stream|⏳ Not started|Replaces old clap-only trigger|
|5 — Full Conversation Loop|⏳ Not started||
|6 — Battery Monitoring|⏳ Not started|Code written, not wired|
|7 — Polish & Personality|⏳ Not started||
|8 — Wake Word|🔮 Future|Server-side "Lumi" detection designed|
|9 — Memory System|🔮 Future||
|10 — Emotion States|🔮 Future||

---

## Phase 1 — Server Foundation ✅ COMPLETE

_Goal: Laptop responds to a test audio file with BMO's voice._

- [x] FastAPI + Uvicorn, faster-whisper, Ollama, Piper — all Dockerised
- [x] Piper voice model `en_GB-alan-low.onnx` + `.json`
- [x] Ollama with `llama3.2:1b`
- [x] Full pipeline: WAV in → Whisper STT → NLP layer → Ollama → Piper → WAV out
- [x] NLP intent layer — greetings/farewells/time/thanks skip LLM
- [x] Audio normalisation — 16kHz, 16-bit mono PCM
- [x] Docker Compose — health checks, named volumes, restart policies
- [x] PostgreSQL volume fixed for Postgres 18+ (`/var/lib/postgresql` mount)
- [x] Local dev mode — native Ollama via `host.docker.internal`
- [x] Debug endpoints: `/chat`, `/status`, `/health`
- [x] Postman collection — all endpoints tested and passing
- [ ] Pipeline error handler → return fallback WAV on any exception ← **still to do**

---

## Phase 1.3 — BMO Voice 🔄 IN PROGRESS

_Goal: Replace generic Piper voice with a voice that sounds like BMO._

**Approach:** Coqui XTTS v2 voice cloning — local, free, 6s+ reference audio needed.

- [ ] Extract 30–60s clean BMO audio (no music, no SFX)
- [ ] Add `coqui-tts` to Docker image
- [ ] Write `xtts_provider.py`
- [ ] Mount reference audio at `/app/data/xtts/`
- [ ] Add `TTS_PROVIDER=piper|xtts` config switch
- [ ] A/B test on `/api/v1/chat`
- [ ] Tune XTTS speed/temperature for BMO tone

**Done when:** BMO sounds like BMO, not a British man.

---

## Phase 1.7 — WebSocket Layer 📐 DESIGNED, NOT BUILT

_Goal: Replace HTTP audio transfer with persistent WebSocket for low-latency streaming._

This phase upgrades the communication layer before any hardware is connected. The HTTP `/api/v1/talk` endpoint stays for debugging.

**Server tasks:**

- [ ] Implement `/ws/audio` — PCM stream in, WAV out, per session
- [ ] Implement `/ws/control` — persistent command channel, always open
- [ ] Implement `POST /api/v1/wake` — remote override endpoint
- [ ] Wake word check on first audio chunk (Whisper on first ~1s, look for "Lumi")
- [ ] Send `{"cmd":"stop"}` when no wake word found
- [ ] Serve filler phrases via `/api/v1/filler` (random from 5 pre-recorded clips)
- [ ] Pipeline error handler — fallback WAV on exception

**Done when:** You can connect a WebSocket client, stream raw PCM, say "Lumi", and get a WAV back.

---

## Phase 2 — Pico W Basic Connection ⏳

_Goal: Pico W sends audio to the server and plays the response. No OLED, no trigger yet._

- [ ] Flash MicroPython on Pico W
- [ ] Connect to WiFi (`network` module)
- [ ] Wire MAX98357 (GP10/GP11/GP12) and test tone playback
- [ ] Connect to `/ws/audio` WebSocket
- [ ] Send hardcoded PCM chunk (silence or tone), receive WAV response
- [ ] Play received WAV via I2S
- [ ] Confirm audio plays cleanly through speaker

**Done when:** Pico W plays BMO's voice through the speaker from a hardcoded trigger.

> Start here. No OLED. No mic. Just: Pico connects, sends bytes, plays bytes back.

---

## Phase 3 — OLED Face ⏳

_Goal: BMO has eyes and expressions that change with state._

- [ ] Wire OLED via I2C (GP4 SDA / GP5 SCL)
- [ ] Flash `ssd1306` driver
- [ ] Draw idle face — simple open eyes
- [ ] Draw listening animation — blinking / pulsing
- [ ] Draw thinking animation — scrolling dots or scan line
- [ ] Draw speaking animation — mouth movement or waveform bars
- [ ] Draw battery low face
- [ ] Implement face state machine: IDLE → LISTENING → THINKING → SPEAKING → REARMING → IDLE

**Done when:** Face changes correctly for each state during a full conversation loop.

---

## Phase 4 — Noise Trigger + Audio Streaming ⏳

_Goal: Noise causes BMO to start streaming. Silence causes it to stop._

Replaces the old clap-only trigger design. Uses `NOISE_THRESHOLD` for all decisions.

**Wiring:**

- [ ] Wire MAX9814 mic to GP26 (ADC0)
- [ ] Wire sound sensor to GP15 (digital pre-filter)
- [ ] Move battery divider to GP27 (ADC1) — frees GP26 for mic

**Firmware:**

- [ ] Implement `read_chunk()` — 512 samples, returns (bytes, peak)
- [ ] Calibrate `NOISE_THRESHOLD` — measure mic swing at normal speech volume
- [ ] Implement rapid-change trigger — silent→loud within 150ms opens stream
- [ ] Open `/ws/audio` on trigger
- [ ] Stream PCM chunks until: server stop / local silence timeout / hard timeout
- [ ] Send `{"cmd":"end_stream", "reason":"..."}` on close
- [ ] Implement `wait_for_rearm()` — 1000ms silence before re-arming
- [ ] Open `/ws/control` on boot — keep permanently open
- [ ] Handle `{"cmd":"force_wake"}` on control channel

**Done when:** Speaking near BMO opens a stream. Silence closes it. Speaker doesn't re-trigger mic.

**Key constants to tune:**

```python
NOISE_THRESHOLD         = 2000   # calibrate during mic test
RAPID_CHANGE_WINDOW_MS  = 150
SILENCE_TIMEOUT_MS      = 2000
STREAM_MAX_MS           = 10000
REARM_SILENCE_MS        = 1000
```

---

## Phase 5 — Full Conversation Loop ⏳

_Goal: Say "Lumi, what time is it?" and hear BMO reply. End-to-end, fully wireless._

- [ ] Trigger → stream → wake word check → pipeline → response plays
- [ ] OLED transitions correctly through all states
- [ ] Filler phrase plays during THINKING state
- [ ] No wake word → silent close, no response, re-arm
- [ ] Remote override works: `POST /api/v1/wake` → Pico listens
- [ ] End-to-end latency measured and under 3 seconds

**Done when:** The full loop works reliably 10 times in a row.

---

## Phase 6 — Battery Monitoring ⏳

_Goal: BMO knows its energy level and warns before dying._

- [ ] Wire voltage divider to GP27 (100kΩ / 100kΩ)
- [ ] Poll `read_battery_voltage()` every 60 seconds
- [ ] Display battery % in OLED corner during IDLE
- [ ] At < 20% — show low battery face
- [ ] At < 10% — BMO says "I'm getting sleepy... my batteries are low"
- [ ] Report battery level to server via control WS heartbeat

**Done when:** Battery % shows on OLED and BMO warns you when low.

---

## Phase 7 — Polish & Personality ⏳

_Goal: BMO feels alive, not like a demo._

- [ ] 5+ filler phrases, randomly selected
- [ ] Random idle animations (slow blink, eyes shift)
- [ ] Boot sequence — OLED wakes up, BMO says "Hello!" on first power-on
- [ ] Shutdown sequence — slide switch off → BMO says goodbye
- [ ] Conversation cooldown — no re-trigger within 2 seconds of finishing
- [ ] Tune system prompt with hardware-specific personality details
- [ ] Adjust XTTS voice speed for BMO's upbeat character

**Done when:** BMO feels like a companion, not a prototype.

---

## Phase 8 — Wake Word (Future) 🔮

_Goal: Fully on-device "Lumi" detection without server round-trip._

Current design uses server-side Whisper for wake word — works fine but adds ~300ms. True on-device would be faster and more robust offline.

- [ ] Research TFLite Micro on RP2040 (MicroPython support status)
- [ ] Find/train keyword model for "Lumi" (~50KB target)
- [ ] Replace noise-trigger with on-device keyword detection
- [ ] Keep noise trigger as fallback

> Do not attempt until Phase 1–7 are complete and stable.

---

## Phase 9 — Memory System (Future) 🔮

_Goal: BMO remembers past conversations within and across sessions._

- [ ] Rolling buffer in Redis — last N exchanges per session
- [ ] Inject history into Ollama context window
- [ ] BMO references things said earlier in the same conversation
- [ ] Persist to PostgreSQL between sessions
- [ ] BMO can say "Last time we spoke, you mentioned..."

---

## Phase 10 — Emotion States (Future) 🔮

_Goal: BMO has moods that influence how it speaks and looks._

- [ ] 4 states: Curious / Playful / Tired / Supportive
- [ ] Battery level → tiredness (low battery = tired BMO)
- [ ] Time of day → morning energy, evening calm
- [ ] Conversation length → enthusiasm decays over long sessions
- [ ] State injected into system prompt dynamically
- [ ] OLED face expression varies per emotion
- [ ] TTS speed/temperature shifts per emotion (XTTS supports this)

---

## Key Code Reference

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

### Battery Monitor (GP27)

```python
from machine import ADC, Pin

batt_adc = ADC(Pin(27))   # GP27 — not GP26 (reserved for mic)

def read_battery_voltage():
    raw = batt_adc.read_u16()
    adc_voltage = raw * 3.3 / 65535
    return round(adc_voltage * 2, 2)

def battery_percent(v):
    if v >= 4.1: return 100
    elif v >= 3.7: return 60
    elif v >= 3.5: return 40
    elif v >= 3.2: return 20
    elif v >= 3.0: return 10
    else: return 0
```

### Read Mic Chunk

```python
from machine import ADC, Pin
import struct

mic = ADC(Pin(26))
CHUNK_SIZE = 512
NOISE_THRESHOLD = 2000  # tune during calibration

def read_chunk():
    samples = []
    for _ in range(CHUNK_SIZE):
        raw = mic.read_u16()
        pcm = raw - 32768         # unsigned → signed 16-bit
        samples.append(pcm)
    peak = max(abs(s) for s in samples)
    buf = struct.pack('<' + 'h' * CHUNK_SIZE, *samples)
    return buf, peak
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

_Last updated: 2026-06-09_ _Hardware locked. No upgrades. Build with what you have._