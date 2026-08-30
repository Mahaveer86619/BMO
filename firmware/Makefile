# BMO Pico firmware workflow — MicroPython + mpremote
#
# One-time setup:
#   sudo pacman -S --needed uv     # if not already installed
#   uv tool install mpremote       # installs `mpremote` onto PATH (~/.local/bin)
#
# Usage (run from repo root or from firmware/):
#   make -C firmware help

PORT := $(shell ls /dev/ttyACM0 2>/dev/null || ls /dev/ttyUSB0 2>/dev/null)

ifeq ($(PORT),)
CONNECT :=
else
CONNECT := connect $(PORT)
endif

.PHONY: help port ls monitor run upload put reset hard-reset

help:
	@echo "make port                                  - show detected Pico serial port"
	@echo "make ls                                     - list files currently on the board"
	@echo "make monitor                                - open serial REPL (Ctrl-] to exit)"
	@echo "make run FILE=tests/01_oled_test.py         - run a script live, nothing saved to flash"
	@echo "make upload                                  - copy lib/ + main.py to the board, then reset into it"
	@echo "make put SRC=lib/sh1106.py [DST=sh1106.py] - copy one arbitrary file to the board"
	@echo "make reset                                   - soft reset (Ctrl-D equivalent, re-runs main.py)"
	@echo "make hard-reset                              - hard reset via DTR toggle"

port:
	@if [ -z "$(PORT)" ]; then \
		echo "No Pico found on /dev/ttyACM* or /dev/ttyUSB*. Plug it in, or check 'ls /dev/tty*' —"; \
		echo "if VC-02's own CH340 USB-serial is also plugged in, it usually shows up as ttyUSB*"; \
		echo "while the Pico is ttyACM* — unplug one if this picks the wrong device."; \
		exit 1; \
	fi
	@echo "$(PORT)"

ls: port
	mpremote $(CONNECT) fs ls

monitor: port
	mpremote $(CONNECT) repl

run: port
	@if [ -z "$(FILE)" ]; then echo "Usage: make run FILE=tests/01_oled_test.py"; exit 1; fi
	mpremote $(CONNECT) run $(FILE)

put: port
	@if [ -z "$(SRC)" ]; then echo "Usage: make put SRC=lib/sh1106.py [DST=sh1106.py]"; exit 1; fi
	mpremote $(CONNECT) fs cp $(SRC) :$(if $(DST),$(DST),$(notdir $(SRC)))

upload: port
	@if [ -d lib ] && [ -n "$$(ls -A lib 2>/dev/null)" ]; then \
		mpremote $(CONNECT) fs cp -r lib :lib; \
	fi
	@if [ -f main.py ]; then \
		mpremote $(CONNECT) fs cp main.py :main.py + soft-reset; \
	else \
		echo "No firmware/main.py yet — nothing to boot into. Use 'make run FILE=...' to try individual test scripts."; \
	fi

reset: port
	mpremote $(CONNECT) soft-reset

hard-reset: port
	mpremote $(CONNECT) reset
