"""
Stage 1 — Sound Sensor / Fallback Trigger (see notes/Hardware.md#Step 2)

Not the primary trigger (VC-02 is) — this is the dormant TRIGGER_MODE=fallback path.
Kept wired and tested anyway; it's free insurance if VC-02 ever mishears you or drops out.

Wiring:
  Sound Sensor VCC -> Pico 3V3
  Sound Sensor GND -> Pico GND
  Sound Sensor DO  -> Pico GP15 (pin 20)
  Sound Sensor AO  -> leave unconnected

Adjust the pot on the sensor board first: should trigger on a normal speaking voice,
not background noise.

Run live, Ctrl-C to stop:
  make -C firmware run FILE=tests/04_sound_sensor_test.py
"""

from machine import Pin
import time

sound = Pin(15, Pin.IN)

print("Watching for trigger... (Ctrl-C to stop)")
while True:
    if sound.value() == 1:
        print("Trigger!")
    time.sleep(0.05)
