# BMO AI Service

Internal-only Python/FastAPI service — bound to `127.0.0.1:8500` inside the container, never
exposed on its own port (see `server/Dockerfile` / `docker-compose.yml`). The Go hub
(`server/cmd`) is its only caller, over `internal/aiclient`. Both processes run in the same
container, started by `supervisord` (see `server/supervisord.conf`) — one monolithic image,
one `docker compose up`.

**Why split at all, if it's one image?** Go stays the thing that's always connected to the
Pico (WebSockets, control channel, health) — a job it's well suited to and already has
wired up. Python owns everything LLM/audio-shaped, because that's where the actual
ecosystem lives (`faster-whisper`, `TTS`/XTTS, `librosa`, `sentence-transformers`, LangChain) —
none of those have real Go equivalents. LangChain specifically so a "tier" in the router is
just a `ChatOllama` or a `ChatOpenAI`-shaped call — swapping providers, or adding a genuinely
different one (e.g. `langchain_anthropic.ChatAnthropic`), never touches the router's call
sites or the Go side at all.

## Endpoints (all under `/internal`, called by Go — not for direct external use)

| Method | Path | Status |
|---|---|---|
| `GET` | `/internal/health` | ✅ working |
| `GET` | `/internal/status` | ✅ working — reports `compute_mode` (cpu/cuda), cloud-escalation flag, Ollama base URL |
| `POST` | `/internal/chat` | ✅ working — `{"messages": [...], "tier": "fast"\|"reasoning"\|"cloud"}` → `{"reply": "...", "tier": "..."}` |
| `POST` | `/internal/stt` | 🚧 stub, 501 — faster-whisper goes here |
| `POST` | `/internal/tts` | 🚧 stub, 501 — Piper/XTTS goes here |

Verified locally (see conversation): `/internal/chat` with `tier: "fast"` against a real
local `llama3.2:1b` returns a real reply; `tier: "cloud"` correctly 502s while
`LLM_PROVIDER_CLOUD_ENABLED=false` (the default — see the data-boundary rule in
`notes/Software.md`).

## Layout

```
ai/
  requirements.txt
  app/
    main.py          — FastAPI app, mounts routes/internal.py
    config.py         — env-driven settings (pydantic-settings)
    compute.py         — GPU/CPU mode detection (see below)
    llm/
      base.py           — LLMProvider interface
      ollama_provider.py — local Ollama via langchain-ollama
      api_provider.py    — any OpenAI-compatible endpoint via langchain-openai
      router.py           — tier name -> live provider instance
    routes/
      internal.py          — the endpoints above
```

## GPU/CPU mode

Two different decisions, at two different times:

- **Build time** — the `ENABLE_GPU` build arg (`server/Dockerfile`) decides whether CUDA-enabled
  `torch` wheels get installed into the image at all. Off by default (this project's baseline
  hardware is an i5 laptop, CPU-only — see `notes/Software.md`'s dev notes).
- **Runtime** — `docker/entrypoint.sh` probes `nvidia-smi` on container start and exports
  `BMO_COMPUTE_MODE=cuda|cpu`; `app/compute.py`'s `detect_compute_mode()` reads that (falling
  back to `torch.cuda.is_available()` or its own `nvidia-smi` probe if run outside the
  container, e.g. local dev) so STT/TTS code can pick a device once it exists.

You can't usefully toggle CUDA-vs-CPU *library* presence at container runtime without
shipping both — that's why it's a build arg, not something `compute.py` decides on its own.

## Local dev (outside Docker)

```bash
cd server/ai
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8500 --reload
```

Requires Ollama reachable at `OLLAMA_BASE_URL` (default `http://localhost:11434`) with at
least `ollama pull llama3.2:1b` done once.

## Not built yet

STT (`faster-whisper`), TTS (Piper/XTTS), the NLP fast-path, the memory graph
(`pgvector` tables), vault tool-calling, and the actual tier-selection logic (which query
needs `fast` vs `reasoning` vs `cloud` — currently the caller just picks). All speced in
`notes/Software.md`; none of it is this service's current job.
