"""
Stage 1, Step 2 — WiFi (see notes/BMO – Full Build Roadmap.md#WiFi Connection)

Create firmware/wifi_secrets.py first (gitignored):
  SSID = "your-network"
  PASSWORD = "your-password"

Run live:
  make -C firmware run FILE=tests/02_wifi_test.py
"""

import network
import time

try:
    from wifi_secrets import SSID, PASSWORD
except ImportError:
    raise SystemExit(
        "Missing firmware/wifi_secrets.py — create it with SSID and PASSWORD "
        "(see firmware/README.md)"
    )


def connect_wifi(ssid, password, timeout_s=15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > timeout_s:
            raise RuntimeError("WiFi connect timed out")
        time.sleep(0.5)

    print("Connected:", wlan.ifconfig())
    return wlan


connect_wifi(SSID, PASSWORD)
