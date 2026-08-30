#!/bin/sh
set -e

OLLAMA_URL="http://127.0.0.1:11434"
DEFAULT_MODELS="${OLLAMA_DEFAULT_MODELS:-llama3.2:1b}"

echo "[bootstrap] waiting for ollama..."
until curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; do
    sleep 1
done
echo "[bootstrap] ollama is up"

for model in $DEFAULT_MODELS; do
    if ollama list | awk 'NR>1{print $1}' | grep -qx "$model"; then
        echo "[bootstrap] $model already present, skipping"
    else
        echo "[bootstrap] pulling $model ..."
        ollama pull "$model"
    fi
done

echo "[bootstrap] done"
