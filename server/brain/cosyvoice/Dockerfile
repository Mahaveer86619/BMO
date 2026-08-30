# CosyVoice TTS service
# Builds from source during `docker compose build --profile cosyvoice`.
# Models are downloaded into the cosyvoice_models volume on first `docker compose up`.
#
# GPU acceleration (recommended):
#   Pass --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cu121
#   and uncomment the `deploy` section in docker-compose.yml.

FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps: sox for audio processing, git for clone, ffmpeg for format support
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        ffmpeg \
        sox \
        libsox-dev \
        build-essential \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# PyTorch — CPU by default.
# For GPU: docker compose build --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cu121
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir \
    torch==2.3.1 \
    torchaudio==2.3.1 \
    --index-url ${TORCH_INDEX}

# Clone CosyVoice with all submodules (third_party/Matcha-TTS etc.)
RUN git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git /opt/cosyvoice \
    && cd /opt/cosyvoice \
    && git submodule update --init --recursive

WORKDIR /opt/cosyvoice

# Install CosyVoice Python deps.
# WeTextProcessing and ttsfrd are Chinese-only normalizers with platform-specific
# wheels — skip them. CosyVoice falls back to WeTextProcessing-lite automatically.
RUN grep -vE '^(WeTextProcessing|ttsfrd)' requirements.txt > /tmp/reqs.txt \
    && pip install --no-cache-dir -r /tmp/reqs.txt \
    && rm /tmp/reqs.txt

# Matcha-TTS is a git submodule that must be installed as a Python package
RUN pip install --no-cache-dir -e third_party/Matcha-TTS

# huggingface_hub for model download in entrypoint
RUN pip install --no-cache-dir huggingface_hub

COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 50000
ENTRYPOINT ["/entrypoint.sh"]
