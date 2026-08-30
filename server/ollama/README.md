# Ollama

No custom code lives here — Ollama itself is handled two different ways depending on which
compose variant is running:

- **`docker-compose.yml` (single image)**: Ollama's binary + GGML backend runners are vendored
  directly into the monolith image in `../Dockerfile` (copied from the official `ollama/ollama`
  image as a build stage), then run as a supervised process alongside the orchestrator and brain
  — see `../supervisord.conf`.
- **`docker-compose.multi.yml` (multi image)**: Ollama runs as the official `ollama/ollama:latest`
  image directly, its own container.

Either way, `../docker/bootstrap.sh` handles pulling the default model(s) on first boot — see that
script and `OLLAMA_DEFAULT_MODELS` in whichever compose file you're using.
