# BMO — top-level dev workflow.
#
# server/ holds everything server-side: orchestrator/ (Go), brain/ (Python),
# db/, redis/, ollama/, storage/ (MinIO's bind-mounted object storage).
#
# Two server topologies, same system either way:
#   single: one image — orchestrator + brain + Ollama, supervised together
#           (server/Dockerfile, server/supervisord.conf, server/docker-compose.yml)
#   multi:  three images — orchestrator/brain/Ollama as separate containers
#           (server/orchestrator/Dockerfile, server/brain/Dockerfile,
#           server/docker-compose.multi.yml)
# Pick one; they use the same ports (4040/5432/6379/9000/9001) so don't run
# both at once. `make down` / `make down-multi` before switching.
#
# Firmware: MicroPython over mpremote (see firmware/Makefile, firmware/README.md).

COMPOSE := docker compose -f server/docker-compose.yml --project-directory server
COMPOSE_MULTI := docker compose -f server/docker-compose.multi.yml --project-directory server

.PHONY: help build up up-build stop down restart logs logs-server logs-db logs-redis logs-storage ps \
        build-multi up-multi up-multi-build stop-multi down-multi logs-multi logs-multi-server logs-multi-brain logs-multi-ollama ps-multi \
        pico-port pico-ls pico-monitor pico-run pico-upload pico-put pico-reset pico-hard-reset

help:
	@echo "Server — single image (Go hub + brain + Ollama, one container):"
	@echo "  make build                    - build the bmo-server image"
	@echo "  make up                       - start everything, detached (builds on first run only)"
	@echo "  make up-build                 - rebuild the image, then start"
	@echo "  make stop                     - stop containers without removing them"
	@echo "  make down                     - stop and remove containers"
	@echo "  make restart                  - restart the bmo-server container only"
	@echo "  make logs                     - follow logs from all services"
	@echo "  make logs-server              - follow bmo-server only (ollama + brain + go, all 3 processes)"
	@echo "  make logs-storage             - follow MinIO (audio storage) logs"
	@echo "  make ps                       - show container status"
	@echo ""
	@echo "Server — multi image (server / brain / Ollama as separate containers):"
	@echo "  make build-multi              - build the server + brain images"
	@echo "  make up-multi                 - start everything, detached (builds on first run only)"
	@echo "  make up-multi-build           - rebuild the images, then start"
	@echo "  make stop-multi               - stop containers without removing them"
	@echo "  make down-multi               - stop and remove containers"
	@echo "  make logs-multi               - follow logs from all services"
	@echo "  make logs-multi-server        - follow the Go container only"
	@echo "  make logs-multi-brain         - follow the brain container only"
	@echo "  make logs-multi-ollama        - follow the ollama container only"
	@echo "  make ps-multi                 - show container status"
	@echo ""
	@echo "Pico (MicroPython over mpremote — see firmware/README.md):"
	@echo "  make pico-port                                  - show detected serial port"
	@echo "  make pico-monitor                               - open serial REPL / live output"
	@echo "  make pico-run FILE=tests/01_oled_test.py        - run a script live, nothing saved to flash"
	@echo "  make pico-upload                                - push firmware/main.py + lib/, reset into it"
	@echo "  make pico-put SRC=lib/sh1106.py                  - copy one arbitrary file to the board"
	@echo "  make pico-ls                                    - list files currently on the board"
	@echo "  make pico-reset                                 - soft reset (re-runs main.py)"
	@echo "  make pico-hard-reset                            - hard reset via DTR toggle"

# --- Server: single image ---

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

logs-storage:
	$(COMPOSE) logs -f storage

ps:
	$(COMPOSE) ps

# --- Server: multi image ---

build-multi:
	$(COMPOSE_MULTI) build

up-multi:
	$(COMPOSE_MULTI) up -d

up-multi-build:
	$(COMPOSE_MULTI) up -d --build

stop-multi:
	$(COMPOSE_MULTI) stop

down-multi:
	$(COMPOSE_MULTI) down

logs-multi:
	$(COMPOSE_MULTI) logs -f

logs-multi-server:
	$(COMPOSE_MULTI) logs -f server

logs-multi-brain:
	$(COMPOSE_MULTI) logs -f brain

logs-multi-ollama:
	$(COMPOSE_MULTI) logs -f ollama

ps-multi:
	$(COMPOSE_MULTI) ps

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
