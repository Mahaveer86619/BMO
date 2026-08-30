#!/bin/sh
set -e

# Decide GPU vs CPU mode for anything in the AI service that branches on it
# (faster-whisper's `device=`, XTTS, etc., once those are wired in — see
# server/ai/app/compute.py). This is a *runtime* check; whether CUDA-enabled
# libraries were even installed into the image is a *build-time* choice —
# the ENABLE_GPU build arg in server/Dockerfile.
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
    echo "[entrypoint] NVIDIA GPU detected -> BMO_COMPUTE_MODE=cuda"
    export BMO_COMPUTE_MODE=cuda
else
    echo "[entrypoint] No usable GPU found -> BMO_COMPUTE_MODE=cpu"
    export BMO_COMPUTE_MODE=cpu
fi

exec supervisord -c /app/supervisord.conf
