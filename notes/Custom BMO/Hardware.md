---
project: "[[Custom BMO – Desk AI Bot]]"
tags:
  - hardware
  - robotics
  - electronics
  - pico-w
---
---

> All components are in hand except the slide switch. Do not buy anything else. Build with what you have.

---

## Component Checklist

|Component|Status|Role|
|---|---|---|
|Raspberry Pi Pico W|✅ Have|Nervous system — WiFi, I2C, I2S, GPIO|
|1.3" OLED Display (I2C 128x64)|✅ Have|BMO's face and status UI|
|8Ω 2W Cavity Speaker|✅ Have|Voice output|
|Sound Sensor Module|✅ Have|Noise gate / pre-filter for trigger|
|2x 18650 Li-ion Batteries|✅ Have|Power source|
|Resistor Kit / Wires|✅ Have|Voltage divider + general wiring|
|MAX98357 I2S 3W Class-D Amp|✅ Have|Clean digital audio output|
|MAX9814 Microphone AGC Amp|✅ Have|Voice capture with auto gain control|
|134N3P Type-C 5V Boost Module|✅ Have|Battery → 5V regulation|
|Slide Switch|❌ Need (~₹30)|Power on/off|

---

## Final Pin Map

| Pico W Pin    | Component                   | Signal          | Notes                                |
| ------------- | --------------------------- | --------------- | ------------------------------------ |
| GP4 (SDA)     | OLED Display                | I2C Data        |                                      |
| GP5 (SCL)     | OLED Display                | I2C Clock       |                                      |
| GP10          | MAX98357                    | BCLK            | I2S Bit Clock                        |
| GP11          | MAX98357                    | LRC             | I2S Word Select                      |
| GP12          | MAX98357                    | DIN             | I2S Data Out                         |
| GP15          | Sound Sensor                | DO              | Digital noise gate trigger           |
| GP26 (ADC0)   | MAX9814                     | Audio In        | Mic ADC — primary audio input        |
| GP27 (ADC1)   | Voltage Divider             | Battery Monitor | Moved from GP26 to free ADC0 for mic |
| VSYS (pin 39) | 134N3P OUT + MAX98357 VIN   | 5V rail         |                                      |
| 3V3 (pin 36)  | OLED, Sound Sensor, MAX9814 | 3.3V logic      |                                      |
| GND           | All components              | Common ground   |                                      |

> **Note:** Battery monitor moved to GP27 to keep GP26 exclusively for the MAX9814 microphone. Update battery code accordingly — `ADC(Pin(27))` not `ADC(Pin(26))`.

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
import ssd1306

i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
print(i2c.scan())  # expect [60] = 0x3C
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
oled.text("BMO online", 0, 28)
oled.show()
```

If `i2c.scan()` returns `[]`, drop freq to `100000`. If still empty, swap SDA/SCL wires. If address is `61` (0x3D) instead of `60`, update the driver init accordingly.

---

### Step 2 — Sound Sensor

Noise gate only — not the primary audio source. Wakes the Pico from idle loop cheaply.

```
Sound Sensor VCC → Pico 3V3
Sound Sensor GND → Pico GND
Sound Sensor DO  → Pico GP15  (pin 20)
Sound Sensor AO  → leave unconnected
```

Adjust the pot on the sensor board: triggers on a normal speaking voice, not background noise. Start with claps, then calibrate down.

**Test:**

```python
from machine import Pin
import time

sound = Pin(15, Pin.IN)
while True:
    if sound.value() == 1:
        print("Trigger!")
    time.sleep(0.05)
```

---

### Step 3 — MAX9814 Microphone

Primary audio input. AGC handles volume differences automatically.

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

**Calibrating NOISE_THRESHOLD:** Run this test, speak at normal volume, note the peak swing from baseline. Set `NOISE_THRESHOLD` in firmware to ~60–70% of that swing.

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

### Step 4 — MAX98357 I2S Amplifier

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

Silent output: check VSYS power. Buzzing/noise: confirm all three I2S pins are correct. Speaker polarity doesn't affect function but swap wires if audio sounds phased.

---

### Step 5 — Battery Voltage Divider

> Use GP27 — not GP26 (GP26 is reserved for the microphone).

```
Battery+  →  R1 (100kΩ)  →  GP27 (ADC1, pin 32)  →  R2 (100kΩ)  →  GND
```

**Code (updated for GP27):**

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

---

### Step 6 — Power System

> Test on USB first. Wire batteries last.

```
2x 18650 in series  →  134N3P IN+ / IN-
134N3P OUT+         →  Slide Switch terminal 1
Slide Switch term 2 →  Pico VSYS  (pin 39)
134N3P OUT-         →  Pico GND
```

**Before connecting Pico:** measure 134N3P output with multimeter. Must read 4.9–5.1V. If it reads 7V+: the boost module is misconfigured — do not connect until fixed.

Two 18650s in series = ~7.4V nominal. The 134N3P regulates this to clean 5V.

---

## Audio State Machine — What the Firmware Does

The Pico runs a simple 5-state machine. States map directly to OLED face expressions.

```
IDLE
  └─ sound sensor OR noise threshold crossed → LISTENING
  └─ remote override command received → LISTENING

LISTENING
  └─ WebSocket open, PCM chunks streaming to server
  └─ server sends {"cmd":"stop"} (no wake word) → IDLE (silent, no response)
  └─ server sends {"cmd":"stop"} (wake word found, response coming) → THINKING

THINKING
  └─ waiting for server to finish pipeline
  └─ filler phrase plays during this state

SPEAKING
  └─ WAV response received, playing via I2S
  └─ audio finishes → REARMING

REARMING
  └─ wait for REARM_SILENCE_MS of mic silence
  └─ prevents speaker output from re-triggering
  └─ silence confirmed → IDLE
```

---

## Noise Threshold — Single Value, All Decisions

```python
NOISE_THRESHOLD = 2000   # tune this during Step 3 mic calibration
```

This one value controls:

- **Trigger detection** — rapid change (silent→loud within 150ms) opens stream
- **In-stream silence detection** — silence for 2000ms closes stream
- **Re-arm** — confirms room quiet before watching again

Tune once during mic calibration. All behaviour adjusts together.

---

## WebSocket Channels

|Channel|Endpoint|Lifetime|Purpose|
|---|---|---|---|
|Control|`ws://<server>:8000/ws/control`|Always open|Remote override, server→Pico commands|
|Audio|`ws://<server>:8000/ws/audio`|Per session only|Raw PCM stream up, WAV response down|

Control WS stays open permanently. Audio WS opens on trigger, closes after response. Keeps Pico memory clean.

---

## Debugging Reference

|Problem|Likely Cause|Fix|
|---|---|---|
|`i2c.scan()` returns `[]`|Wrong pins or freq too high|Try `freq=100000`, check SDA/SCL swap|
|OLED address `0x3D` not `0x3C`|Board variant|Pass `0x3D` to driver init|
|Mic pegged at 0 or 65535|VDD not connected or wiring fault|Check 3V3 and GND on MAX9814|
|Mic baseline not ~32768|ADC float or bad ground|Ensure solid GND connection|
|No audio from speaker|VSYS not powering MAX98357|MAX98357 needs 5V — use VSYS not 3V3|
|I2S buzzing / noise|Wrong pin assignment|Confirm BCLK=GP10, LRC=GP11, DIN=GP12|
|Garbled audio playback|Wrong sample rate|Server must send 16kHz, 16-bit, mono PCM|
|Pico can't reach server|Server not binding to 0.0.0.0|`uvicorn main:app --host 0.0.0.0 --port 8000`|
|Battery reading wrong|Still on GP26|Move voltage divider to GP27|
|Stream opens on background noise|Threshold too low|Raise `NOISE_THRESHOLD`, recalibrate|
|Speaker re-triggers listening|Re-arm not waiting|Increase `REARM_SILENCE_MS`|
|134N3P output > 5.1V|Module not configured|Do not connect Pico until fixed|