"""
Stage 1, Step 5 — MAX98357 I2S Amplifier (see notes/Hardware.md#Step 5)

Wiring (needs 5V — VSYS, not 3V3):
  MAX98357 VIN  -> Pico VSYS (pin 39)
  MAX98357 GND  -> Pico GND
  MAX98357 BCLK -> Pico GP10 (pin 14)
  MAX98357 LRC  -> Pico GP11 (pin 15)
  MAX98357 DIN  -> Pico GP12 (pin 16)
  Speaker +/-   -> MAX98357 OUT+/OUT-

Run live:
  make -C firmware run FILE=tests/03_i2s_tone_test.py
"""

from machine import I2S, Pin
import struct
import math

audio_out = I2S(
    0,
    sck=Pin(10),
    ws=Pin(11),
    sd=Pin(12),
    mode=I2S.TX,
    bits=16,
    format=I2S.MONO,
    rate=16000,
    ibuf=4096,
)

samples = [int(32767 * math.sin(2 * math.pi * 440 * i / 16000)) for i in range(16000)]
buf = struct.pack("<" + "h" * len(samples), *samples)

print("Playing 440Hz tone for 1 second...")
audio_out.write(buf)
print("Done. Silent output -> check VSYS power. Buzzing -> check BCLK/LRC/DIN pin assignment.")
