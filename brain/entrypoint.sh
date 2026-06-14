#!/usr/bin/env bash
# BMO brain startup: pre-download models into their volumes, then start the server.
# Subsequent restarts skip downloads if the .ready marker files exist.
set -euo pipefail

WHISPER_MODEL="${WHISPER_MODEL:-base}"
WHISPER_CACHE="${WHISPER_MODEL_CACHE:-/app/data/whisper}"
XTTS_CACHE="${XTTS_CACHE_DIR:-/app/data/xtts}"
TTS_PROVIDER="${TTS_PROVIDER:-piper}"

echo "=============================="
echo "  BMO brain — init"
echo "=============================="

# ── Whisper STT ────────────────────────────────────────────────────────────────
mkdir -p "${WHISPER_CACHE}"
WHISPER_MARKER="${WHISPER_CACHE}/.ready-${WHISPER_MODEL}"

if [ ! -f "${WHISPER_MARKER}" ]; then
    echo "[init] Downloading Whisper '${WHISPER_MODEL}' model..."
    python3 - <<PYEOF
from faster_whisper import WhisperModel
WhisperModel(
    "${WHISPER_MODEL}",
    device="cpu",
    compute_type="int8",
    download_root="${WHISPER_CACHE}",
)
print("[init] Whisper '${WHISPER_MODEL}' downloaded.")
PYEOF
    touch "${WHISPER_MARKER}"
    echo "[init] Whisper ready."
else
    echo "[init] Whisper '${WHISPER_MODEL}' already cached — skipping download."
fi

# ── XTTS v2 (only when TTS_PROVIDER=xtts) ─────────────────────────────────────
if [ "${TTS_PROVIDER}" = "xtts" ]; then
    mkdir -p "${XTTS_CACHE}"
    XTTS_MARKER="${XTTS_CACHE}/.ready-xtts-v2"

    if [ ! -f "${XTTS_MARKER}" ]; then
        echo "[init] Downloading XTTS v2 model (~1.8 GB) ..."
        TTS_HOME="${XTTS_CACHE}" COQUI_TOS_AGREED=1 python3 - <<PYEOF
import os
os.environ["TTS_HOME"] = "${XTTS_CACHE}"
os.environ["COQUI_TOS_AGREED"] = "1"
from TTS.api import TTS
TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False, progress_bar=True)
print("[init] XTTS v2 downloaded.")
PYEOF
        touch "${XTTS_MARKER}"
        echo "[init] XTTS v2 ready."
    else
        echo "[init] XTTS v2 already cached — skipping download."
    fi
fi

# ── Kokoro-82M (only when TTS_PROVIDER=kokoro) ────────────────────────────────
if [ "${TTS_PROVIDER}" = "kokoro" ]; then
    KOKORO_CACHE="${KOKORO_CACHE_DIR:-/app/data/kokoro}"
    mkdir -p "${KOKORO_CACHE}"
    KOKORO_MARKER="${KOKORO_CACHE}/.ready-kokoro-82m"

    if [ ! -f "${KOKORO_MARKER}" ]; then
        echo "[init] Downloading Kokoro-82M model (~330MB)..."
        HF_HOME="${KOKORO_CACHE}" python3 - <<PYEOF
import os
os.environ["HF_HOME"] = "${KOKORO_CACHE}"
from kokoro import KPipeline
KPipeline(lang_code="${KOKORO_LANG:-a}")
print("[init] Kokoro-82M downloaded.")
PYEOF
        touch "${KOKORO_MARKER}"
        echo "[init] Kokoro-82M ready."
    else
        echo "[init] Kokoro-82M already cached — skipping download."
    fi
fi

echo "[init] Starting BMO brain server..."
echo "=============================="
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info
