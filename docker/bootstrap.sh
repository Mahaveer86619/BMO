#!/bin/sh
set -e

# OLLAMA_URL defaults to the monolith's own localhost Ollama. In the
# multi-image compose file this is overridden to http://ollama:11434 so the
# same script works unmodified against a separate ollama container — pure
# HTTP calls, no dependency on the `ollama` CLI binary being present.
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
DEFAULT_MODELS="${OLLAMA_DEFAULT_MODELS:-llama3.2:1b}"

echo "[bootstrap] waiting for ollama at $OLLAMA_URL ..."
until curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; do
    sleep 1
done
echo "[bootstrap] ollama is up"

for model in $DEFAULT_MODELS; do
    if curl -sf "$OLLAMA_URL/api/tags" | grep -qF "\"name\":\"$model\""; then
        echo "[bootstrap] $model already present, skipping"
    else
        echo "[bootstrap] pulling $model ..."
        curl -sf -X POST "$OLLAMA_URL/api/pull" -d "{\"name\":\"$model\"}"
        echo "[bootstrap] $model pulled"
    fi
done

echo "[bootstrap] done"
