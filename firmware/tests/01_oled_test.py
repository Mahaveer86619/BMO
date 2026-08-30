"""
Stage 1, Step 1 — OLED Display (see notes/Hardware.md#Step 1)

Wiring:
  OLED VCC -> Pico 3V3  (pin 36)
  OLED GND -> Pico GND  (pin 38)
  OLED SDA -> Pico GP4  (pin 6)
  OLED SCL -> Pico GP5  (pin 7)

Requires ssd1306.py on the board first:
  make -C firmware put SRC=lib/ssd1306.py

Run live (nothing saved to flash):
  make -C firmware run FILE=tests/01_oled_test.py
"""

from machine import Pin, I2C
import ssd1306

i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
addrs = i2c.scan()
print("i2c.scan() ->", [hex(a) for a in addrs])
# Expect [0x3c]. If empty: drop freq to 100000, or check for an SDA/SCL swap.
# If the address is 0x3d instead of 0x3c, pass addr=0x3d to SSD1306_I2C below.

oled = ssd1306.SSD1306_I2C(128, 64, i2c)
oled.fill(0)
oled.text("BMO online", 0, 28)
oled.show()
print("OLED should now show 'BMO online'")
