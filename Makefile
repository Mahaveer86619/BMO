# BMO — top-level dev workflow.
# Server: one Docker image (Go hub + Python AI service + Ollama, supervised together
# — see server/Dockerfile, server/supervisord.conf). Firmware: MicroPython over mpremote
# (see firmware/Makefile, firmware/README.md).

COMPOSE := docker compose -f server/docker-compose.yml --project-directory server

.PHONY: help build up up-build stop down restart logs logs-server logs-db logs-redis ps \
        pico-port pico-ls pico-monitor pico-run pico-upload pico-put pico-reset pico-hard-reset

help:
	@echo "Server (Docker — Go hub + Python AI + Ollama, one image):"
	@echo "  make build                    - build the bmo-server image"
	@echo "  make up                       - start everything, detached (builds on first run only)"
	@echo "  make up-build                 - rebuild the image, then start"
	@echo "  make stop                     - stop containers without removing them"
	@echo "  make down                     - stop and remove containers"
	@echo "  make restart                  - restart the bmo-server container only"
	@echo "  make logs                     - follow logs from all services"
	@echo "  make logs-server              - follow bmo-server only (ollama + ai + go, all 3 processes)"
	@echo "  make ps                       - show container status"
	@echo ""
	@echo "Pico (MicroPython over mpremote — see firmware/README.md):"
	@echo "  make pico-port                                  - show detected serial port"
	@echo "  make pico-monitor                               - open serial REPL / live output"
	@echo "  make pico-run FILE=tests/01_oled_test.py        - run a script live, nothing saved to flash"
	@echo "  make pico-upload                                - push firmware/main.py + lib/, reset into it"
	@echo "  make pico-put SRC=lib/ssd1306.py                - copy one arbitrary file to the board"
	@echo "  make pico-ls                                    - list files currently on the board"
	@echo "  make pico-reset                                 - soft reset (re-runs main.py)"
	@echo "  make pico-hard-reset                            - hard reset via DTR toggle"

# --- Server ---

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

up-build:
	$(COMPOSE) up -d --build

stop:
	$(COMPOSE) stop

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart bmo-server

logs:
	$(COMPOSE) logs -f

logs-server:
	$(COMPOSE) logs -f bmo-server

logs-db:
	$(COMPOSE) logs -f postgres

logs-redis:
	$(COMPOSE) logs -f redis

ps:
	$(COMPOSE) ps

# --- Pico ---

pico-port:
	@$(MAKE) -C firmware port

pico-ls:
	@$(MAKE) -C firmware ls

pico-monitor:
	@$(MAKE) -C firmware monitor

pico-run:
	@$(MAKE) -C firmware run FILE=$(FILE)

pico-upload:
	@$(MAKE) -C firmware upload

pico-put:
	@$(MAKE) -C firmware put SRC=$(SRC) DST=$(DST)

pico-reset:
	@$(MAKE) -C firmware reset

pico-hard-reset:
	@$(MAKE) -C firmware hard-reset
