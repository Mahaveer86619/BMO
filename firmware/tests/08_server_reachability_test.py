"""
Stage 2, Checkpoint A — server reachability (see notes/BMO – Full Build Roadmap.md
#Stage 2 — Connectivity Checkpoints)

"Proves nothing more than Pico can talk to the laptop — do this before debugging
anything more complex." Needs only WiFi wired (no OLED/mic/amp/VC-02 required),
and the server running (`make up` from repo root).

Add SERVER_HOST to firmware/wifi_secrets.py (gitignored, same file as SSID/PASSWORD):
  SERVER_HOST = "192.168.1.6"   # your laptop's LAN IP — check with `hostname -I`

Uses raw sockets, not urequests — one less library to install on the board for
a one-shot GET.

Run live:
  make -C firmware run FILE=tests/08_server_reachability_test.py
"""

import network
import socket
import time

try:
    from wifi_secrets import SSID, PASSWORD, SERVER_HOST
except ImportError:
    raise SystemExit(
        "Missing SSID/PASSWORD/SERVER_HOST in firmware/wifi_secrets.py — "
        "see firmware/README.md"
    )

SERVER_PORT = 4040
PATH = "/api/v1/health"


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


def http_get(host, port, path, timeout_s=10):
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.settimeout(timeout_s)
    s.connect(addr)
    request = "GET {} HTTP/1.0\r\nHost: {}\r\nConnection: close\r\n\r\n".format(path, host)
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
    return response.decode()


connect_wifi(SSID, PASSWORD)
print("Requesting http://{}:{}{} ...".format(SERVER_HOST, SERVER_PORT, PATH))
print(http_get(SERVER_HOST, SERVER_PORT, PATH))
