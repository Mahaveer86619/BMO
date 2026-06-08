FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Piper TTS — extract to /opt/piper and symlink binary into PATH
RUN mkdir -p /opt/piper && \
    curl -fsSL https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz \
    | tar -xzC /opt/piper --strip-components=1 && \
    ln -s /opt/piper/piper /usr/local/bin/piper

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
