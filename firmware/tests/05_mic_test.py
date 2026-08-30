"""
Stage 1, Step 3 — MAX9814 Microphone / Content Capture (see notes/Hardware.md#Step 3)

This is the mic that feeds Whisper — not the one VC-02 uses to recognize the wake phrase.

Wiring:
  MAX9814 VDD  -> Pico 3V3
  MAX9814 GND  -> Pico GND
  MAX9814 Out  -> Pico GP26 (ADC0, pin 31)
  MAX9814 Gain -> leave floating (mid gain, good default)
  MAX9814 AR   -> leave floating

Two modes below — raw baseline read, and swing calibration for the fallback trigger's
NOISE_THRESHOLD constant. Silence baseline should read ~32000-33500; voice should swing
noticeably above/below. Pegged at 0 or 65535 means a wiring fault.

Run live, Ctrl-C to stop:
  make -C firmware run FILE=tests/05_mic_test.py
"""

from machine import ADC, Pin
import time

mic = ADC(Pin(26))

MODE = "baseline"  # "baseline" | "calibrate"

if MODE == "baseline":
    print("Reading raw ADC values... (Ctrl-C to stop)")
    while True:
        print(mic.read_u16())
        time.sleep(0.01)
else:
    print("Calibrating NOISE_THRESHOLD (fallback trigger only)... (Ctrl-C to stop)")
    baseline = 32768
    while True:
        val = mic.read_u16()
        swing = abs(val - baseline)
        if swing > 500:
            print("Peak swing:", swing)
        time.sleep(0.005)
