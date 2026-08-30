"""
Sanity check #0 — before any wiring at all. Confirms MicroPython is actually
running on the board and can control hardware, using only the Pico W's
onboard LED (no external components, no breadboard needed).

On the Pico W specifically, the onboard LED is wired through the CYW43439
WiFi chip's GPIO, not a plain RP2040 pin — MicroPython exposes it uniformly
as the logical name "LED" so this works the same whether it's a plain Pico
or a Pico W.

Run live, Ctrl-C to stop:
  make pico-run FILE=tests/00_led_blink_test.py
"""

from machine import Pin
import time

led = Pin("LED", Pin.OUT)

print("Blinking onboard LED... (Ctrl-C to stop)")
while True:
    led.toggle()
    time.sleep(0.5)
