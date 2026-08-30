"""
Stage 1, Step 1 — OLED Display (see notes/Hardware.md#Step 1)

This 1.3" OLED uses an SH1106 controller, not SSD1306 — same I2C address
(0x3C) and physical footprint, but a different addressing model (132
internal columns, page-mode-only writes) that an SSD1306 driver
misinterprets. Confirmed the hard way this session, and previously
documented in notes/oled_bringup_final.html from the C firmware bring-up —
check that file's "Root Cause" section if this ever comes up again.

Wiring:
  OLED VCC -> Pico 3V3  (pin 36)
  OLED GND -> Pico GND  (pin 3, or any GND)
  OLED SDA -> Pico GP4  (pin 6)
  OLED SCL -> Pico GP5  (pin 7)

Requires sh1106.py on the board first:
  make -C firmware put SRC=lib/sh1106.py

Run live (nothing saved to flash):
  make -C firmware run FILE=tests/01_oled_test.py
"""

from machine import Pin, I2C
import sh1106

i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
addrs = i2c.scan()
print("i2c.scan() ->", [hex(a) for a in addrs])
# Expect [0x3c].

oled = sh1106.SH1106_I2C(128, 64, i2c)
oled.fill(0)
oled.text("BMO online", 0, 28)
oled.show()
print("OLED should now show 'BMO online'")
