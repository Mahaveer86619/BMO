#!/usr/bin/env bash
# CosyVoice TTS service startup.
# Downloads the model into the mounted volume on first run, then starts the server.
# Subsequent starts skip the download if the .ready marker file exists.
set -euo pipefail

# Configurable via docker-compose environment
MODEL_NAME="${COSYVOICE_MODEL:-CosyVoice2-0.5B}"
HF_REPO="${COSYVOICE_HF_REPO:-FunAudioLLM/CosyVoice2-0.5B}"
MODEL_DIR="/models/${MODEL_NAME}"
PORT="${COSYVOICE_PORT:-50000}"

echo "=============================="
echo "  CosyVoice — init"
echo "  model : ${HF_REPO}"
echo "  dir   : ${MODEL_DIR}"
echo "=============================="

mkdir -p "${MODEL_DIR}"
MARKER="${MODEL_DIR}/.ready"

if [ ! -f "${MARKER}" ]; then
    echo "[init] Downloading ${HF_REPO} from HuggingFace (first run — this may take a few minutes)..."
    python3 - <<PYEOF
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="${HF_REPO}",
    local_dir="${MODEL_DIR}",
    ignore_patterns=["*.msgpack", "flax_model*", "tf_model*"],
)
print("[init] Model download complete.")
PYEOF
    touch "${MARKER}"
    echo "[init] Model ready at ${MODEL_DIR}."
else
    echo "[init] Model already present — skipping download."
fi

echo "[init] Starting CosyVoice FastAPI server on :${PORT}..."
echo "=============================="
cd /opt/cosyvoice/runtime/python/fastapi
exec python3 server.py --port "${PORT}" --model_dir "${MODEL_DIR}"
