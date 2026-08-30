"""
Runs continuously instead of drawing once and exiting — closer to how the
real firmware will behave (always redrawing, never a one-shot script).

Ctrl-C to stop.

Run live:
  make -C firmware run FILE=tests/01f_oled_test_loop.py
"""

from machine import Pin, I2C
import sh1106
import time

i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
print("i2c.scan() ->", [hex(a) for a in i2c.scan()])

oled = sh1106.SH1106_I2C(128, 64, i2c)

print("Looping — Ctrl-C to stop.")
count = 0
while True:
    oled.fill(0)
    oled.text("BMO online", 0, 20)
    oled.text("count: {}".format(count), 0, 40)
    oled.show()
    count += 1
    time.sleep_ms(500)
