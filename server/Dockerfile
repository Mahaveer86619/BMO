# ==========================================
# Stage 1: Build the Go binary — the always-on hub the Pico connects to
# ==========================================
FROM golang:alpine AS go-builder

WORKDIR /app/go

COPY go.mod go.sum ./
RUN go mod download

COPY cmd ./cmd
COPY internal ./internal

RUN CGO_ENABLED=0 GOOS=linux go build -o /app/bmo-server ./cmd/main.go

# ==========================================
# Stage 2: Vendor Ollama's binary + its GGML backend runners from the official
# image, rather than reinstalling it — those runner .so files (CPU/CUDA/Vulkan)
# are what actually need libvulkan1/libopenblas0 below.
# ==========================================
FROM ollama/ollama:latest AS ollama-src

# ==========================================
# Stage 3: Runtime — Go binary + Python AI service + Ollama, one image, one
# process tree. Go is the only externally-facing process; Ollama and the AI
# service both bind 127.0.0.1 and are reachable only from inside this
# container. Supervised together by supervisord so one restarting doesn't
# kill the others, and a bootstrap step pulls the default Ollama model(s) on
# first run only (see docker/bootstrap.sh) — nothing to set up by hand.
# ==========================================
FROM python:3.12-slim

# Set to "true" to install CUDA-enabled torch for local GPU inference (STT/TTS,
# once those are wired in — see server/ai/requirements.txt). Ollama's own GPU
# support doesn't need this — it's already built into the vendored binary/runners
# above and only needs the GPU passed through (see docker-compose.yml). Which
# mode actually gets *used* at runtime is decided separately by
# docker/entrypoint.sh probing nvidia-smi.
ARG ENABLE_GPU=false

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates tzdata curl ffmpeg libvulkan1 libopenblas0 && \
    rm -rf /var/lib/apt/lists/*

# Ollama — binary + its backend runner payloads
COPY --from=ollama-src /bin/ollama /usr/bin/ollama
COPY --from=ollama-src /lib/ollama /usr/lib/ollama

# Go binary
COPY --from=go-builder /app/bmo-server /app/bmo-server

# Python AI service
COPY ai/requirements.txt /app/ai/requirements.txt
RUN pip install --no-cache-dir -r /app/ai/requirements.txt supervisor && \
    if [ "$ENABLE_GPU" = "true" ]; then \
        pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cu121; \
    fi
COPY ai/app /app/ai/app

# Process supervision + first-run bootstrap + GPU/CPU mode detection
COPY supervisord.conf /app/supervisord.conf
COPY docker/entrypoint.sh /app/entrypoint.sh
COPY docker/bootstrap.sh /app/docker/bootstrap.sh
RUN chmod +x /app/entrypoint.sh /app/docker/bootstrap.sh

# Go's public port. Ollama (11434) and the Python AI service (8500) are
# intentionally NOT exposed — internal-only, reachable over localhost inside
# this one container.
EXPOSE 4040

ENTRYPOINT ["/app/entrypoint.sh"]
