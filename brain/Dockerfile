FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    curl \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Piper TTS binary
RUN mkdir -p /opt/piper && \
    curl -fsSL https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz \
    | tar -xzC /opt/piper --strip-components=1 && \
    ln -s /opt/piper/piper /usr/local/bin/piper

# Download Piper voice model (~63MB) so fillers work on first container start
RUN mkdir -p /opt/piper-models && \
    curl -fsSL -o /opt/piper-models/en_GB-alan-low.onnx \
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/low/en_GB-alan-low.onnx" && \
    curl -fsSL -o /opt/piper-models/en_GB-alan-low.onnx.json \
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/low/en_GB-alan-low.onnx.json"

# Pin torch + torchaudio together from the CPU wheel index.
# TTS==0.22.0 depends on torchaudio — if we don't pin it here it pulls a CUDA build
# that was compiled against a different torch version and fails to dlopen at runtime.
RUN pip install --no-cache-dir \
    torch==2.2.0 \
    torchaudio==2.2.0 \
    --index-url https://download.pytorch.org/whl/cpu

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
