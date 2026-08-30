"""
Stage 2 — continuous health display. Connects WiFi once, then loops forever:
every 5s, polls GET /api/v1/health on the server, and shows on the OLED
both the server's uptime (server/orchestrator/internal/services/health_service.go's
UptimeSeconds) and the Pico's own uptime (time since this script started).

Needs OLED wired (Step 1) and firmware/wifi_secrets.py with SSID/PASSWORD/SERVER_HOST
(see firmware/README.md).

Ctrl-C to stop.

Run live:
  make -C firmware run FILE=tests/09_health_display.py
"""

from machine import Pin, I2C
import sh1106
import network
import socket
import json
import time

try:
    from wifi_secrets import SSID, PASSWORD, SERVER_HOST
except ImportError:
    raise SystemExit(
        "Missing SSID/PASSWORD/SERVER_HOST in firmware/wifi_secrets.py — see firmware/README.md"
    )

SERVER_PORT = 4040
POLL_INTERVAL_S = 5


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


def fetch_health(host, port, timeout_s=5):
    """GET /api/v1/health, return the parsed JSON body."""
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.settimeout(timeout_s)
    s.connect(addr)
    request = "GET /api/v1/health HTTP/1.0\r\nHost: {}\r\nConnection: close\r\n\r\n".format(host)
    s.send(request.encode())

    response = b""
    while True:
        try:
            chunk = s.recv(512)
        except OSError:
            break
        if not chunk:
            break
        response += chunk
    s.close()

    # Body is whatever follows the first blank line after the HTTP headers.
    body = response.split(b"\r\n\r\n", 1)[1]
    return json.loads(body)


def format_uptime(total_seconds):
    """Compact uptime string: '45s', '3m12s', '1h05m', '2d03h'."""
    total_seconds = int(total_seconds)
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)

    if days:
        return "{}d{:02d}h".format(days, hours)
    if hours:
        return "{}h{:02d}m".format(hours, minutes)
    if minutes:
        return "{}m{:02d}s".format(minutes, seconds)
    return "{}s".format(seconds)


i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
oled = sh1106.SH1106_I2C(128, 64, i2c)

connect_wifi(SSID, PASSWORD)
boot_ticks = time.ticks_ms()

print("Polling http://{}:{}/api/v1/health every {}s... (Ctrl-C to stop)".format(
    SERVER_HOST, SERVER_PORT, POLL_INTERVAL_S
))

while True:
    pico_uptime_s = time.ticks_diff(time.ticks_ms(), boot_ticks) // 1000

    oled.fill(0)
    oled.text("BMO health", 0, 0)

    try:
        health = fetch_health(SERVER_HOST, SERVER_PORT)
        status = health.get("status", "?")
        server_uptime_s = health.get("uptime_seconds", 0)
        print("status={}  server_uptime={}s  pico_uptime={}s".format(
            status, server_uptime_s, pico_uptime_s
        ))
        oled.text("Server: {}".format(status), 0, 16)
        oled.text("Srv up: {}".format(format_uptime(server_uptime_s)), 0, 32)
    except Exception as e:
        print("poll failed:", e)
        oled.text("Server: down", 0, 16)

    oled.text("Pico up: {}".format(format_uptime(pico_uptime_s)), 0, 48)
    oled.show()

    time.sleep(POLL_INTERVAL_S)
