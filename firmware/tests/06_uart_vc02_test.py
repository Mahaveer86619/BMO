"""
Stage 1, Step 4b — VC-02 UART echo test (see notes/Hardware.md#Step 4)

IMPORTANT: configure VC-02 first via voice.ai-thinker.com over its own USB-serial (step 4a)
BEFORE wiring it to the Pico. Wake phrase + hard commands must already be flashed onto
the module, and you need the exported protocol reference to know which byte(s) mean which
command below — do not guess the frame layout.

Wiring:
  VC-02 VCC -> Pico VSYS (pin 39) — NOT 3V3, VC-02 needs >= 3.6V
  VC-02 GND -> Pico GND
  VC-02 TX1 -> Pico GP1 (UART0 RX)
  VC-02 RX1 -> Pico GP0 (UART0 TX)

Run live, say your wake phrase, Ctrl-C to stop:
  make -C firmware run FILE=tests/06_uart_vc02_test.py

If nothing arrives: confirm VCC is on VSYS (won't boot below 3.6V — the #1 suspect),
confirm TX1/RX1 aren't swapped, confirm baud is 115200 (VC-02 default), and re-test the
wake phrase on the bare Kit via its own USB-serial link before blaming the Pico wiring.
"""

from machine import UART, Pin
import time

uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))

print("Listening for VC-02 UART bytes... (Ctrl-C to stop)")
while True:
    if uart.any():
        data = uart.read()
        print("VC-02:", data)
    time.sleep(0.05)
