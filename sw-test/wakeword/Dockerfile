FROM python:3.11-slim

# PortAudio (required by pyaudio) + ALSA headers for mic access
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    portaudio19-dev \
    libasound2-dev \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download openWakeWord models at build time so runtime is offline
RUN python -c "import openwakeword; openwakeword.utils.download_models()"

COPY . .

ENTRYPOINT ["python", "test_wakeword.py"]
CMD ["--help"]
