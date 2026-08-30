"""
Stage 1, Step 6 — Battery Voltage Divider (see notes/Hardware.md#Step 6)

Use GP27, not GP26 (GP26 is reserved for the MAX9814 mic).

Wiring:
  Battery+ -> R1 (100k) -> GP27 (ADC1, pin 32) -> R2 (100k) -> GND

Thresholds below assume a resting/full pack voltage of ~4.2V (true for the corrected
PARALLEL battery wiring — see notes/Hardware.md#Power Planning). Re-verify against your
actual pack with a multimeter once wired.

Run live, Ctrl-C to stop:
  make -C firmware run FILE=tests/07_battery_test.py
"""

from machine import ADC, Pin
import time

batt_adc = ADC(Pin(27))


def read_battery_voltage():
    raw = batt_adc.read_u16()
    adc_voltage = raw * 3.3 / 65535
    battery_voltage = adc_voltage * 2  # 50/50 divider
    return round(battery_voltage, 2)


def battery_percent(voltage):
    if voltage >= 4.1:
        return 100
    elif voltage >= 3.7:
        return 60
    elif voltage >= 3.5:
        return 40
    elif voltage >= 3.2:
        return 20
    elif voltage >= 3.0:
        return 10
    else:
        return 0


print("Reading battery voltage... (Ctrl-C to stop)")
while True:
    v = read_battery_voltage()
    print(f"{v}V -> {battery_percent(v)}%")
    time.sleep(1)
