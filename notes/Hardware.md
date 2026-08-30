---
project: "[[Custom BMO – Desk AI Bot]]"
tags:
  - hardware
  - robotics
  - electronics
  - pico-w
  - vc-02
status: In Development
last_updated: 2026-08-29
---
---

> This hardware set was revised once, deliberately, to add the VC-02 wake-word module — because a guessed noise-threshold trigger was never going to be reliable, and a real assistant needs a real "ears" stage. **This is the last hardware change.** Everything else — memory, personality, tool use, moods — is built in software from here. Do not buy anything not on this list.

---

## Why VC-02 Changes the Design

The old design made the Pico itself decide "was that speech?" from a raw ADC swing on the MAX9814 — fragile, noisy-room-sensitive, and it burned Pico CPU cycles on a job Pico was never good at.

VC-02 is a dedicated speech-recognition chip. It does **one job** — listen constantly and recognize a small trained vocabulary (wake phrase + a few hard commands) — entirely offline, and hands the Pico a clean UART message when something matches. This does not replace the MAX9814. It replaces the *sound sensor's guesswork*.

**Division of labor, permanently:**

| Ear | Job | Feeds |
|---|---|---|
| VC-02 + its own mic capsule | "Was I addressed? Was it a hard command?" — nothing else | Pico, over UART, instantly, no network |
| MAX9814 + Pico ADC | "What did they actually say?" — the real content | Server, over WebSocket, for Whisper |

These are two separate microphones on two separate signal paths. Do not try to share one capsule between them — VC-02 expects a specific electret capture level (see its own application circuit), and splitting a MAX9814's AGC'd output into it will fight the chip's own gain control.

Sound sensor module: demoted, not discarded. It's already in your hands and costs nothing to keep wired — it becomes a **fallback trigger** (rapid noise-change heuristic, same as the old design) that only matters if VC-02 fails to boot, misconfigures, or reliably mishears your particular wake phrase. Primary trigger is always VC-02.

---

## Component Checklist

| Component                                                 | Status                 | Role                                                                 |
| --------------------------------------------------------- | ---------------------- | -------------------------------------------------------------------- |
| Raspberry Pi Pico W                                       | ✅ Have                 | Nervous system — WiFi, I2C, I2S, UART, ADC, GPIO                     |
| 1.3" OLED Display (I2C 128x64)                            | ✅ Have                 | BMO's face and status UI                                             |
| 8Ω 2W Cavity Speaker                                      | ✅ Have                 | Voice output (driven via MAX98357, not VC-02's own SPK pins)         |
| Sound Sensor Module                                       | ✅ Have                 | Fallback trigger only — VC-02 is primary                             |
| 2x 18650 Li-ion Batteries                                 | ✅ Have                 | Power source — **wire in PARALLEL, not series** (see Power Planning) |
| Resistor Kit / Wires                                      | ✅ Have                 | Voltage divider + general wiring                                     |
| MAX98357 I2S 3W Class-D Amp                               | ✅ Have                 | Drives the real speaker for all TTS output                           |
| MAX9814 Microphone AGC Amp                                | ✅ Have                 | Content-capture mic — feeds Whisper, not VC-02                       |
| 134N3P Type-C 5V Boost/Charge Module                      | ✅ Have                 | Single-cell (1S) only — confirms the parallel wiring fix below       |
| Slide Switch                                              | ✅ Have                 | Power on/off                                                         |
| Ai-Thinker **VC-02-Kit** (dev board, not bare SMD module) | ✅ Have                 | Offline wake-phrase + hard-command recognition                       |
| Electret mic capsule for VC-02                            | Bundled with VC-02-Kit | VC-02's dedicated "was I addressed?" ear                             |

**Buy the VC-02-Kit, not the bare VC-02 module.** The bare part is an SMD-20 castellated-edge package at 18×17×3.2mm with a fine enough pitch that Ai-Thinker's own datasheet includes a reflow-oven soldering profile for it — not a hand-assembly part. The Kit breaks 19 of the 20 signals out to a 2.54mm-pitch DIP header, bundles a matched analog mic module and a small speaker (for VC-02's own onboard prompts — unrelated to BMO's main speaker), and has an onboard CH340C USB-serial chip so you can flash/train it directly from a PC without a separate programmer. Runs ~₹550–760 depending on vendor. Same pin functions either way — everything below applies to both.

**Confirmed from vendor documentation:** VC-02 sends a **command ID (a hex code) over UART** when it recognizes something — never raw audio. This is the hard confirmation behind the mic-separation design above: there is no way to get spoken content out of VC-02, by design, so MAX9814 staying on its own path is not optional, it's the only way BMO hears actual words. Ai-Thinker's config tool also lets you map a recognized command directly to a **GPIO pin action** (documented for driving relays/LEDs) as an alternative to parsing the UART hex code — worth using for your hard commands (`stop`, `mute`, …) to skip host-side parsing entirely, if you want the absolute lowest latency path. Confirm the exact pin/mode when you train your set in the platform.

---

## ⚠️ Power Planning — Read Before Wiring Anything

### Fix: battery wiring must be PARALLEL, not series

The original plan called for "2x 18650 in series → 134N3P → VSYS," reasoning that two cells in series (7.4–8.4V) get bucked down to 5V. **This is wrong and would put the module out of spec, possibly damaging it.**

The 134N3P is a **single-cell (1S)** Li-ion boost + charge/protection board:

| Spec | Value |
|---|---|
| Input voltage | 3.7–5.5V (one cell only) |
| Output | 5V, up to 1A |
| Charging | Preset 4.2V, ±1% — assumes exactly one cell |
| Efficiency | ~85% (3.7V in → 5V/1A out) |

Two 18650s in series (7.4V nominal, up to 8.4V full charge) exceeds its 5.5V input ceiling and breaks its charge logic (which is calibrated for one 4.2V-max cell), even before considering the boost stage itself.

**Fix:** wire the two 18650s in **parallel** — join both `+` terminals together, both `–` terminals together — before the 134N3P's `BAT+`/`BAT–` input. This keeps pack voltage at a safe 3.7V nominal while doubling capacity (mAh) for roughly double the runtime, and lets the 134N3P's built-in USB-C charge circuit safely top up both cells at once through one port — something series wiring never gave you anyway.

Use two cells of matched age/capacity, ideally from the same batch — parallel cells should be reasonably matched so one doesn't backfeed the other on connection or take a disproportionate share of charge/discharge current.

```
18650 #1 (+) ──┬── 134N3P BAT+
18650 #2 (+) ──┘
18650 #1 (–) ──┬── 134N3P BAT–
18650 #2 (–) ──┘
```

### VC-02 needs the 5V rail, not 3V3

VC-02's `VCC` minimum is **3.6V** — it will not run reliably (or at all) on the Pico's 3.3V rail. Its logic pins (UART, GPIO) *are* 3.3V level and interface directly with the Pico, but power must come from VSYS (post-134N3P, 5V), same rail as the MAX98357. Getting this backwards is the single most likely first-bring-up mistake — check it with a multimeter before connecting the Pico.

### Current budget

Approximate draws — measure your actual units once assembled, these are typical/datasheet figures for planning:

| Component | State | Draw |
|---|---|---|
| Pico W | WiFi connected, idle | ~80 mA |
| OLED SSD1306 | Idle face | ~15 mA |
| MAX98357 | Quiescent (no audio) | ~4 mA |
| MAX9814 | Always on | ~3 mA |
| VC-02 | Standby / always listening | ~56 mA (datasheet: 55.7–56.6 mA) |
| VC-02 | Active recognition burst | up to ~230 mA, sub-second |
| Sound sensor (fallback) | Always on | ~5 mA |
| **Idle total (continuous)** | | **~163 mA** |
| MAX98357 while speaking | Conversational volume, not full 3W | +150–300 mA transient |

**VC-02's ~56mA standby draw is, after the Pico itself, the single largest continuous line item** — it's the price of always-on wake detection. With a ~5000mAh pack (2×2500mAh 18650s in parallel) at 3.7V nominal through the 134N3P at ~85% efficiency, that's roughly **18 hours of pure idle-listening runtime** before considering any actual conversations. Fine for "desk companion that gets put on charge overnight," not fine for "runs untethered for a week."

**Practical takeaway (also used by the ambient-transcription feature in [[Software]]):** treat BMO as USB/mains-powered most of the time — battery is for portability and outage backup, not primary power. Don't design any feature (server or firmware) assuming it can run on battery indefinitely.

---

## Final Pin Map

| Pico W Pin | Component | Signal | Notes |
|---|---|---|---|
| GP0 | VC-02 `RX1` | UART0 TX (Pico → VC-02) | |
| GP1 | VC-02 `TX1` | UART0 RX (VC-02 → Pico) | **Primary trigger channel** — wake phrase + hard-command IDs arrive here |
| GP16, GP17 *(optional)* | VC-02 `SDA`, `SCL` (repurposed as plain GPIO) | Direct hard-command pulse | Only if you use GPIO-per-command mapping instead of/alongside UART — see Step 4 |
| GP4 (SDA) | OLED | I2C Data | |
| GP5 (SCL) | OLED | I2C Clock | |
| GP10 | MAX98357 | BCLK | I2S Bit Clock |
| GP11 | MAX98357 | LRC | I2S Word Select |
| GP12 | MAX98357 | DIN | I2S Data Out |
| GP28 (ADC2) | Sound Sensor | AO | **Fallback trigger only** — VC-02 UART is primary. DO is dead on this unit (comparator stuck HIGH regardless of trim pot — confirmed on real hardware, see notes/sound_sensor_final.html) — AO + software threshold is the only working path, moved here (not GP26) since that's the mic's |
| GP26 (ADC0) | MAX9814 | Audio In | Content-capture mic — separate mic from VC-02 |
| GP27 (ADC1) | Voltage Divider | Battery Monitor | Moved from GP26 to free ADC0 for the mic |
| VSYS (pin 39) | 134N3P OUT+, MAX98357 VIN, **VC-02 VCC** | 5V rail | VC-02 minimum is 3.6V — must not go on 3V3 |
| 3V3 (pin 36) | OLED, Sound Sensor, MAX9814 | 3.3V logic | |
| GND | All components | Common ground | |

> VC-02's `MIC+`/`MIC-` and `SPK+`/`SPK-` are not in this table — they connect to VC-02's own bundled mic capsule and are otherwise unused (see Step 4 below). Nothing on VC-02 shares a signal with the Pico except VCC, GND, and the two UART lines.

---

## Wiring Guide — Do In This Order

Wire and test one component at a time. Never wire everything at once.

---

### Step 1 — OLED Display

```
OLED VCC  → Pico 3V3  (pin 36)
OLED GND  → Pico GND  (pin 38)
OLED SDA  → Pico GP4  (pin 6)
OLED SCL  → Pico GP5  (pin 7)
```

**Test:**

```python
from machine import Pin, I2C
import sh1106

i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
print(i2c.scan())  # expect [60] = 0x3C
oled = sh1106.SH1106_I2C(128, 64, i2c)
oled.text("BMO online", 0, 28)
oled.show()
```

**This is an SH1106 panel, not SSD1306** — same address and footprint, but a different addressing model
(132 internal columns, page-mode-only writes). An SSD1306 driver against this panel either times out or
gets ACKed while displaying garbage — confirmed the hard way, see notes/oled_bringup_final.html. Use
`sh1106.py` (robert-hh/SH1106 on GitHub), not micropython-lib's `ssd1306.py`.

If `i2c.scan()` returns `[]`, drop freq to `100000`. If still empty, check for a loose wire before assuming
it's a pin/address problem — a marginal connection can make `scan()` flicker between finding and not
finding the device. If the address is `61` (0x3D) instead of `60`, pass `addr=0x3D` to `SH1106_I2C`.

---

### Step 2 — Sound Sensor (Fallback Trigger)

Not the primary trigger anymore — VC-02 (Step 4) is. Keep it wired anyway; it's free insurance if VC-02 ever mishears you or drops out.

**DO is dead on this unit** — the onboard comparator stays stuck HIGH no matter how the trim pot is set
(confirmed on real hardware, see notes/sound_sensor_final.html). Don't bother wiring it. Use AO with a
software threshold instead — strictly better anyway (no mechanical pot to drift, threshold tunable in
firmware). AO needs an ADC pin, and GP26 is already the mic's — use GP28 (ADC2), the only ADC pin still free.

```
Sound Sensor VCC → Pico 3V3
Sound Sensor GND → Pico GND
Sound Sensor AO  → Pico GP28  (ADC2, pin 34)
Sound Sensor DO  → leave unconnected
```

**Test:**

```python
from machine import ADC, Pin
import time

sensor = ADC(Pin(28))
THRESHOLD = 500  # ADC counts (12-bit-scaled) — see calibration data below

while True:
    val = sensor.read_u16() >> 4  # scale 16-bit read_u16() down to the 12-bit range calibration used
    if val > THRESHOLD:
        print("Trigger! peak =", val)
    time.sleep(0.005)
```

**Calibration data from real hardware** (12-bit scale, 0–4095): idle baseline ~150, ambient room noise
peaks ~390, normal clap/speech 500–1700, loud clap/shouting 2000–3600. `THRESHOLD=500` sits above measured
ambient noise with some margin — the original bring-up's `THRESHOLD=250` was *below* its measured ambient
peak (~390) and risked false triggers in a noisy room; don't reuse that value. Longer-term this should be
auto-calibrated from a few seconds of silence on boot rather than a fixed constant — noted but not built.

---

### Step 3 — MAX9814 Microphone (Content Capture)

This is the mic that actually feeds Whisper — not the one VC-02 uses to recognize the wake phrase. AGC handles volume differences automatically.

```
MAX9814 VDD  → Pico 3V3
MAX9814 GND  → Pico GND
MAX9814 Out  → Pico GP26  (ADC0, pin 31)
MAX9814 Gain → leave floating  (mid gain — good default)
MAX9814 AR   → leave floating
```

**Test:**

```python
from machine import ADC, Pin
import time

mic = ADC(Pin(26))
while True:
    val = mic.read_u16()
    print(val)
    time.sleep(0.01)
```

Silence baseline: ~32000–33500. Voice: values swing noticeably above/below. If pegged at 0 or 65535 — check wiring.

**Calibrating `NOISE_THRESHOLD` (for the fallback trigger only):**

```python
baseline = 32768
while True:
    val = mic.read_u16()
    swing = abs(val - baseline)
    if swing > 500:
        print(f"Peak swing: {swing}")
    time.sleep(0.005)
```

---

### Step 4 — VC-02 Wake & Hard-Command Module (NEW)

Two phases: **configure first, wire second.** The configuration step needs a direct USB link to your PC and cannot happen once VC-02 is buried inside BMO.

#### 4a. Configure (before wiring to Pico)

1. Connect the VC-02-Kit to your PC via its onboard USB-serial (CH340).
2. Go to Ai-Thinker's voice platform (`voice.ai-thinker.com`) and train:
   - **1 wake phrase** — e.g. "Hey BMO" — this is what opens the conversation pipeline.
   - **A handful of hard commands** that should work instantly with zero network round-trip: `stop`, `mute`, `volume up`, `volume down`, `snooze`. Keep this list short — VC-02 supports up to 150 local commands total, but every one you add is one more thing that can be misheard. Hard commands are for actions that must never wait on WiFi or the LLM, not a replacement for open-ended conversation.
3. Export/flash the trained set to the module. **Note the exported protocol docs/sample code** — the exact UART frame format (which byte means which command) is generated per your trained set by Ai-Thinker's tool, not fixed in the base VC-02 datasheet. You'll need that exported reference for Pico-side parsing in [[Software]].

#### 4b. Wire (after configuration)

The mic capsule and bundled speaker are true zero-solder plug-ins on this board — both terminate in a 2-pin JST connector that clicks straight into a matching connector on the board silkscreened `MIC+`/`MIC-` and `SPK+`/`SPK-`. Nothing to solder for either. The board also breaks out a dedicated 4-pin header (separate from the long edge headers) that's almost certainly `VCC`/`GND`/`TX1`/`RX1` pre-populated with pins — confirm against the silkscreen next to it, then run jumper wires straight from there.

```
VC-02 VCC   → Pico VSYS (pin 39)   — NOT 3V3, VC-02 needs ≥3.6V
VC-02 GND   → Pico GND
VC-02 TX1   → Pico GP1 (UART0 RX)
VC-02 RX1   → Pico GP0 (UART0 TX)
VC-02 MIC+/MIC- → mic capsule, JST plug-in (already terminated — just click it in)
VC-02 SPK+/SPK- → bundled speaker, JST plug-in — leave unplugged in the final build (it's VC-02's own onboard-prompt speaker, unused; real BMO speech goes through MAX98357). Useful to plug in temporarily during step 4a bring-up so you can hear VC-02 confirm recognition out loud before it's ever wired to the Pico.
VC-02 IOB8       → leave unconnected in the final build (debug log UART only; tap it with a USB-serial adapter during bring-up if something misbehaves)
```

**Optional — direct GPIO path for hard commands.** If you configure GPIO-per-command mapping in step 4a instead of (or alongside) UART, pick 1–2 spare VC-02 GPIOs (`SDA`/pin 8, `SCL`/pin 9, `IOA25`/pin 6 are all free — none are used elsewhere in this design) and wire them to free Pico GPIOs, e.g. `GP16`, `GP17`. This gives your most latency-critical command (likely `stop`, so BMO can be interrupted mid-sentence) a plain digital edge instead of a UART frame to parse. Not required — UART alone is enough to build a working system first.

**Test — confirm bytes arrive on trigger:**

```python
from machine import UART, Pin
import time

uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))

while True:
    if uart.any():
        data = uart.read()
        print("VC-02:", data)
    time.sleep(0.05)
```

Say your wake phrase. You should see bytes arrive. Decode which byte(s) mean "wake" vs. each hard command using the protocol reference exported in step 4a — don't guess the frame layout.

**If nothing arrives:** confirm VCC is on VSYS (module won't boot below 3.6V — this is the #1 suspect), confirm TX1/RX1 aren't swapped, confirm baud is 115200 (VC-02 default), confirm the wake phrase was actually flashed (re-test on the bare Kit via its USB-serial link before blaming the Pico wiring).

---

### Step 5 — MAX98357 I2S Amplifier

Needs 5V — connect to VSYS, not 3V3.

```
MAX98357 VIN   → Pico VSYS  (pin 39)
MAX98357 GND   → Pico GND
MAX98357 BCLK  → Pico GP10  (pin 14)
MAX98357 LRC   → Pico GP11  (pin 15)
MAX98357 DIN   → Pico GP12  (pin 16)
MAX98357 GAIN  → leave floating  (9dB default)
MAX98357 SD    → leave unconnected  (always on)

Speaker +      → MAX98357 OUT+
Speaker -      → MAX98357 OUT-
```

**Test with 440Hz tone:**

```python
from machine import I2S, Pin
import struct, math

audio_out = I2S(
    0,
    sck=Pin(10), ws=Pin(11), sd=Pin(12),
    mode=I2S.TX,
    bits=16,
    format=I2S.MONO,
    rate=16000,
    ibuf=4096
)

samples = [int(32767 * math.sin(2 * math.pi * 440 * i / 16000)) for i in range(16000)]
buf = struct.pack('<' + 'h' * len(samples), *samples)
audio_out.write(buf)
```

Silent output: check VSYS power. Buzzing/noise: confirm all three I2S pins are correct.

---

### Step 6 — Battery Voltage Divider

> Use GP27 — not GP26 (GP26 is reserved for the MAX9814 mic).

```
Battery+  →  R1 (100kΩ)  →  GP27 (ADC1, pin 32)  →  R2 (100kΩ)  →  GND
```

```python
from machine import ADC, Pin

batt_adc = ADC(Pin(27))

def read_battery_voltage():
    raw = batt_adc.read_u16()
    adc_voltage = raw * 3.3 / 65535
    battery_voltage = adc_voltage * 2   # 50/50 divider
    return round(battery_voltage, 2)

def battery_percent(voltage):
    if voltage >= 4.1: return 100
    elif voltage >= 3.7: return 60
    elif voltage >= 3.5: return 40
    elif voltage >= 3.2: return 20
    elif voltage >= 3.0: return 10
    else: return 0
```

> These thresholds assumed a series pack peaking near 4.1–4.2V per the old (incorrect) wiring. With the corrected **parallel** pack, resting/full voltage is still ~4.2V (parallel doesn't change voltage, only capacity), so these thresholds are still valid. Re-verify with a multimeter against your actual pack once wired.

---

### Step 7 — Power System

> Test on USB first. Wire batteries last. **Parallel, not series — see Power Planning above.**

```
18650 #1 (+) ─┬─ 134N3P BAT+          18650 #1 (–) ─┬─ 134N3P BAT–
18650 #2 (+) ─┘                       18650 #2 (–) ─┘

134N3P OUT+         →  Slide Switch terminal 1
Slide Switch term 2 →  Pico VSYS  (pin 39)
134N3P OUT-         →  Pico GND
```

**Before connecting Pico:** measure 134N3P output with a multimeter. Must read 4.9–5.1V. If it reads 7V+, something is still wired as series — stop and recheck the parallel joins above; do not connect the Pico.

Two 18650s in parallel at ~3.7V nominal (matching the 134N3P's 1S input spec) — the module regulates this to a clean, stable 5V regardless of pack capacity.

---

## Debugging Reference

| Problem | Likely Cause | Fix |
|---|---|---|
| `i2c.scan()` returns `[]` | Wrong pins or freq too high | Try `freq=100000`, check SDA/SCL swap |
| OLED address `0x3D` not `0x3C` | Board variant | Pass `0x3D` to driver init |
| Mic pegged at 0 or 65535 | VDD not connected or wiring fault | Check 3V3 and GND on MAX9814 |
| Mic baseline not ~32768 | ADC float or bad ground | Ensure solid GND connection |
| No audio from speaker | VSYS not powering MAX98357 | MAX98357 needs 5V — use VSYS not 3V3 |
| I2S buzzing / noise | Wrong pin assignment | Confirm BCLK=GP10, LRC=GP11, DIN=GP12 |
| Garbled audio playback | Wrong sample rate | Server must send 16kHz, 16-bit, mono PCM |
| Pico can't reach server | Server not binding to 0.0.0.0 | `uvicorn main:app --host 0.0.0.0 --port 8000` |
| Battery reading wrong | Still on GP26 | Move voltage divider to GP27 |
| Stream opens on background noise | Fallback threshold too low | Raise `NOISE_THRESHOLD`, recalibrate (only affects the fallback path) |
| Speaker re-triggers listening | Re-arm not waiting | Increase `REARM_SILENCE_MS` |
| 134N3P output > 5.1V | Battery pack still wired as series | Rewire as parallel — see Power Planning |
| VC-02 never boots / UART silent | VCC on 3V3 instead of VSYS | Move VCC to VSYS (5V); VC-02 needs ≥3.6V |
| VC-02 boots but never recognizes anything | Wake phrase not actually flashed, or mic capsule loose | Re-test on the bare Kit via USB-serial before blaming Pico wiring |
| VC-02 recognizes on the Kit but not once installed | Mic capsule occluded by enclosure, or SPK pins accidentally shorted | Check capsule has a clear air path; confirm SPK+/SPK- left open |
| UART bytes arrive but don't match any known command | Frame format assumed instead of read from export | Use the protocol reference Ai-Thinker's tool generated for *your* trained set, not the base datasheet |
