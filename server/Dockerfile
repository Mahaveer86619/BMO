# Build context is server/ — this image bundles orchestrator/ (Go) and
# brain/ (Python) together. See docker-compose.yml.

# ==========================================
# Stage 1: Build the Go binary — the always-on hub the Pico connects to
# ==========================================
FROM golang:alpine AS go-builder

WORKDIR /app/go

COPY orchestrator/go.mod orchestrator/go.sum ./
RUN go mod download

COPY orchestrator/cmd ./cmd
COPY orchestrator/internal ./internal

RUN CGO_ENABLED=0 GOOS=linux go build -o /app/bmo-server ./cmd/main.go

# ==========================================
# Stage 2: Vendor Ollama's binary + its GGML backend runners from the official
# image, rather than reinstalling it — those runner .so files (CPU/CUDA/Vulkan)
# are what actually need libvulkan1/libopenblas0 below.
# ==========================================
FROM ollama/ollama:latest AS ollama-src

# ==========================================
# Stage 3: Runtime — Go binary + brain (Python) + Ollama, one image, one
# process tree. Go is the only externally-facing process; Ollama and brain
# both bind 127.0.0.1/localhost and are reachable only from inside this
# container. Supervised together by supervisord (supervisord.conf)
# so one restarting doesn't kill the others.
#
# Base image and brain's own dependency setup (piper binary + model, pinned
# CPU torch/torchaudio, ffmpeg/build-essential/libsndfile1) are lifted
# straight from brain/Dockerfile — brain wasn't rewritten, just relocated
# into this shared image.
# ==========================================
FROM python:3.11-slim

# Set to "true" to install CUDA-enabled torch (faster Whisper/XTTS with a
# GPU). Ollama's own GPU support doesn't need this — it's already built into
# the vendored binary/runners above and only needs the GPU passed through
# (see docker-compose.yml). Which mode actually gets *used* at runtime is
# decided separately by docker/entrypoint.sh probing nvidia-smi.
ARG ENABLE_GPU=false

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates tzdata curl ffmpeg build-essential libsndfile1 \
        libvulkan1 libopenblas0 && \
    rm -rf /var/lib/apt/lists/*

# Ollama — binary + its backend runner payloads
COPY --from=ollama-src /bin/ollama /usr/bin/ollama
COPY --from=ollama-src /lib/ollama /usr/lib/ollama

# Go binary
COPY --from=go-builder /app/bmo-server /app/bmo-server

# Piper TTS binary + default voice model (~63MB) — from brain/Dockerfile
RUN mkdir -p /opt/piper && \
    curl -fsSL https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz \
    | tar -xzC /opt/piper --strip-components=1 && \
    ln -s /opt/piper/piper /usr/local/bin/piper
RUN mkdir -p /opt/piper-models && \
    curl -fsSL -o /opt/piper-models/en_GB-alan-low.onnx \
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/low/en_GB-alan-low.onnx" && \
    curl -fsSL -o /opt/piper-models/en_GB-alan-low.onnx.json \
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/low/en_GB-alan-low.onnx.json"

# Pin torch + torchaudio together from the CPU wheel index — TTS==0.22.0
# depends on torchaudio, and an unpinned install pulls a CUDA build compiled
# against a different torch version that fails to dlopen at runtime.
RUN if [ "$ENABLE_GPU" = "true" ]; then \
        pip install --no-cache-dir torch==2.2.0 torchaudio==2.2.0; \
    else \
        pip install --no-cache-dir torch==2.2.0 torchaudio==2.2.0 \
            --index-url https://download.pytorch.org/whl/cpu; \
    fi

WORKDIR /app/brain
COPY brain/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt supervisor

COPY brain/app ./app
COPY brain/static ./static
COPY brain/entrypoint.sh .
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

WORKDIR /app

# Process supervision + GPU/CPU mode detection
COPY supervisord.conf /app/supervisord.conf
COPY docker/entrypoint.sh /app/entrypoint.sh
COPY docker/bootstrap.sh /app/docker/bootstrap.sh
RUN chmod +x /app/entrypoint.sh /app/docker/bootstrap.sh

# Go's public port. Ollama (11434) and brain (8000) are intentionally NOT
# exposed — internal-only, reachable over localhost inside this one container.
EXPOSE 4040

ENTRYPOINT ["/app/entrypoint.sh"]
