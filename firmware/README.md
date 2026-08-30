# BMO Firmware — Dev Workflow

This is the MicroPython side of BMO, developed with **Zed for editing/saving** and **mpremote (terminal) for
upload/run/monitor** — no Thonny needed. Thonny and mpremote both talk to the board the same way (MicroPython's
raw-REPL protocol over USB serial); mpremote is the official CLI-first tool for exactly this workflow and is what
these scripts wrap.

## One-time setup

```bash
sudo pacman -S --needed uv      # fast Python tool installer/runner
uv tool install mpremote        # installs `mpremote` onto ~/.local/bin (already on PATH)
```

Flash MicroPython onto the Pico W once (hold BOOTSEL, plug in USB, drag the `.uf2` from
https://micropython.org/download/RPI_PICO_W/ onto the mounted drive). After that, all uploads happen over the
normal USB-serial connection — no BOOTSEL needed again unless you brick the filesystem.

A udev rule already exists at `/etc/udev/rules.d/99-pico.rules` making both the Pico's BOOTSEL and application-mode
USB IDs world-readable/writable, so no `sudo`/group membership is needed to talk to the board.

## Layout

```
firmware/
  tests/       — standalone bring-up scripts, one per Stage 1 hardware checklist item (see notes/BMO – Full Build Roadmap.md)
  lib/         — shared drivers (e.g. sh1106.py) that need to live on the board's flash to be import-able
  main.py      — the real firmware entry point (not written yet — Stage 3 work, see project root notes)
  wifi_secrets.py  — gitignored; holds SSID/password, imported by scripts that need WiFi
```

## Everyday commands

```bash
make -C firmware help                          # list everything
make -C firmware run FILE=tests/01_oled_test.py  # run a test script live — nothing is saved to flash
make -C firmware monitor                       # serial REPL / live print() output — Ctrl-] to exit
make -C firmware ls                            # what's actually on the board right now
make -C firmware put SRC=lib/sh1106.py         # copy one driver file onto the board's flash
make -C firmware upload                        # push lib/ + main.py, then reset the board into it
```

Same commands are wired into Zed as tasks — open the command palette (`ctrl-shift-p`) → **task: spawn** → pick one
of the "Pico: ..." tasks, or use the keybindings in `~/.config/zed/keymap.json` (added: `ctrl-alt-u` upload,
`ctrl-alt-r` run current file, `ctrl-alt-m` monitor, `ctrl-alt-l` list files). Output shows in Zed's integrated
terminal panel, so you never have to leave the editor.

## `wifi_secrets.py`

Create this file yourself (it's gitignored — don't hardcode credentials into a script that gets committed, unlike
`hw-test/src/main.c` which currently does):

```python
SSID = "your-network"
PASSWORD = "your-password"
SERVER_HOST = "192.168.1.6"   # your laptop's LAN IP — check with `hostname -I`, changes if your router re-DHCPs it
```

**Then upload it to the board — this is easy to miss.** `make pico-run FILE=...` only sends the *one*
script file to the board; it doesn't also send local files that script `import`s. Any test that does
`from wifi_secrets import ...` needs the file actually present on the board's flash first, same as
`lib/sh1106.py`:

```bash
make -C firmware put SRC=wifi_secrets.py
```

Otherwise you'll get `ImportError: no module named 'wifi_secrets'` even though the file clearly exists
locally — it exists on your machine, just not yet on the board.

## Editor autocomplete for `machine` / `network` / `rp2` etc.

These modules only exist on the board — Zed's Python language server can't resolve them by default. Fix once:

```bash
cd firmware
uv venv
uv pip install micropython-rp2-stubs
```

Then point Zed's Python LSP at `firmware/.venv` (Zed auto-detects a `.venv` in the project root it's editing, or
set it explicitly via `pyrightconfig.json` — already added in this directory).

## Test order (matches [[BMO – Full Build Roadmap]] Stage 1)

1. `01_oled_test.py` — I2C scan + "BMO online" on the display
2. `02_wifi_test.py` — connect to WiFi, print the assigned IP
3. `03_i2s_tone_test.py` — 440Hz tone out of the MAX98357 + speaker
4. `04_sound_sensor_test.py` — fallback-trigger digital pin read
5. `05_mic_test.py` — MAX9814 ADC baseline + calibration helper
6. `06_uart_vc02_test.py` — confirm UART bytes arrive from VC-02 on wake phrase
7. `07_battery_test.py` — voltage divider read + percentage mapping

Run them in this order as you wire each component — it mirrors the hardware checklist exactly.

## Stage 2, Checkpoint A — server reachability

8. `08_server_reachability_test.py` — WiFi + a raw-socket `GET /api/v1/health` against the server. Needs only
   WiFi wired (not OLED/mic/amp/VC-02) and the server running (`make up` from repo root). This is the first
   real "Pico talks to the laptop" proof — do it before anything more complex, per
   [[BMO – Full Build Roadmap]]'s Stage 2.
