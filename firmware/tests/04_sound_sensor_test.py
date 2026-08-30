"""
Stage 1 — Sound Sensor / Fallback Trigger (see notes/Hardware.md#Step 2)

Not the primary trigger (VC-02 is) — this is the dormant TRIGGER_MODE=fallback path.

DO is dead on this unit — the onboard comparator stays stuck HIGH regardless of the
trim pot (confirmed on real hardware, see notes/sound_sensor_final.html). Use AO with
a software threshold instead; don't bother wiring DO.

Wiring:
  Sound Sensor VCC -> Pico 3V3
  Sound Sensor GND -> Pico GND
  Sound Sensor AO  -> Pico GP28 (ADC2, pin 34)  -- GP26 is the mic's, GP27 the battery's
  Sound Sensor DO  -> leave unconnected

Calibration data from real hardware (12-bit scale, 0-4095): idle baseline ~150, ambient
room noise peaks ~390, normal clap/speech 500-1700, loud clap/shouting 2000-3600.
THRESHOLD below sits above measured ambient noise with margin.

Run live, Ctrl-C to stop:
  make -C firmware run FILE=tests/04_sound_sensor_test.py
"""

from machine import ADC, Pin
import time

sensor = ADC(Pin(28))
THRESHOLD = 500  # 12-bit-scaled ADC counts — see calibration data above

print("Watching for trigger... (Ctrl-C to stop)")
while True:
    val = sensor.read_u16() >> 4  # scale 16-bit read_u16() down to the 12-bit range calibration used
    if val > THRESHOLD:
        print("Trigger! peak =", val)
    time.sleep(0.005)
