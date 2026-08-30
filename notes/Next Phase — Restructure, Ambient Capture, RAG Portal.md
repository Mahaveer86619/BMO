---
project: "[[Custom BMO – Desk AI Bot]]"
tags:
  - bmo
  - roadmap
  - planning
status: §1 done 2026-08-30 — §2/§3 not started
last_updated: 2026-08-30
---
> Captured 2026-08-30. §1 (directory restructure) got done same-day once hardware bring-up hit a natural
> pause point. §2 (ambient capture) and §3 (RAG portal) are still queued, nothing built there yet.

---

## 1. Directory restructure — one `server/` with a subdir per concern ✅ Done

```
server/
  orchestrator/   Go (cmd/, internal/, go.mod, go.sum, standalone Dockerfile — was server/ directly)
  brain/          Python (app/, static/, entrypoint.sh, requirements.txt, Dockerfile — was ../brain/)
  db/             placeholder — schema is applied by brain/app/db/client.py at runtime, no config here yet
  redis/          placeholder — no custom config yet
  ollama/         no custom code — see server/ollama/README.md for how it's actually run (differs
                  between the single-image and multi-image compose variants)
  storage/        MinIO's object storage, bind-mounted (not a named Docker volume) — real uploaded
                  files directly on disk at server/storage/, browsable/backupable from the host
  Dockerfile              single-image monolith (was repo-root Dockerfile)
  docker-compose.yml       single-image variant (was repo-root)
  docker-compose.multi.yml multi-image variant (was repo-root)
  supervisord.conf
  docker/entrypoint.sh, bootstrap.sh
```

Nesting both `orchestrator/` and `brain/` under `server/` also fixed something the previous root-level
layout got wrong: `server/Dockerfile`'s build context is `server/` again (not the repo root), since both
halves it needs to `COPY` from are now inside that one directory rather than being siblings of it.

The MinIO-vs-plain-directory question resolved as: **keep MinIO, bind-mount its own data directory** —
`server/storage/` is MinIO's literal on-disk backend, so it's simultaneously "a dedicated local directory"
and still reachable through MinIO's API/console, without rewriting `brain/core/storage.py`'s `upload_audio()`
interface to talk to the filesystem directly.

---

## 2. Always-listening raw-audio capture — retroactive VAD buffering

**This is additive, not a replacement.** The existing wake-word → stream → NLP/LLM → TTS flow stays exactly
as it is. This is a second, parallel thing the Pico can do with its always-on mic feed, independent of
whether a wake phrase ever fires.

**The design, as described:**
1. Pico streams raw PCM continuously (not gated on VC-02's wake trigger) — a new mode alongside the
   existing wake-triggered `/ws/talk` stream.
2. The receiving side keeps a short rolling ring buffer of that raw audio (last N seconds).
3. A cheap, fast "is this speech" check runs continuously over the incoming stream (not a full STT pass —
   a lightweight VAD, chunk-by-chunk).
4. Once VAD confidence confirms speech, the confirmation itself arrives *late* relative to when speech
   actually started (VAD needs a few chunks of evidence before it's confident) — so the system tracks
   back into the ring buffer by that confidence-latency to recover the actual start of the utterance,
   not just the point where confidence crossed the threshold.
5. The full utterance (buffered start → detected end-of-speech) gets stored as one clip.
6. Later, an offline post-processing step goes back over stored clips and does *something* with pieces of
   them — exact shape (STT transcription for a searchable log? speaker embeddings? training data?) not
   yet specified — worth pinning down before building step 6, since it changes what step 5 needs to keep.

**Where does the VAD + ring buffer live?** Given the Go/Python split (Go = Pico connection + low-latency
work, Python/brain = heavy lifting), the ring buffer and VAD gate are a natural fit for the **Go side** —
a fast, lightweight VAD (energy-based, or a WebRTC-VAD-style algorithm) run per chunk as it arrives over
the persistent connection, with Go holding the short buffer needed to do the retroactive lookback. Once
Go has assembled a complete utterance, it hands the WAV to brain — either into the same processing path
`/ws/talk` already uses (if this should also get a live reply) or into a separate "just archive it,
no reply" endpoint if this ambient path is meant to run silently in the background. That's an actual
design decision to make when this gets built, not decided here.

**Constraint that no longer applies, per your call:** notes/Software.md's ambient-transcription section
(and BMO – Capability Topics.md's B3) treated always-on capture as the highest-privacy-risk feature and
sequenced it last, behind `BMO_MODE=desk`-gating and a retention policy — reasoning that assumed data
might leave the device. On hardware and a server you own, entirely on your own LAN, with no cloud path,
that risk model doesn't apply — build this whenever it's next in line, not last-and-cautiously. The
retention-window / redaction-command ideas from that section are still worth keeping regardless, just as
plain data-hygiene rather than a security gate.

---

## 3. Portal: knowledge graph viewer + chat with Lumi, RAG-backed

A new web frontend (brain already serves `static/index.html` — this either grows that or replaces it)
showing:
- Findings from the post-processing pipeline above (§2.6)
- A visualization of the knowledge graph (entities/mentions — see notes/Software.md's Personal Memory
  Graph section, `notes/BMO – Capability Topics.md` Topic C1 — not built yet either)
- A chat interface (text and voice) to talk to Lumi directly, with the knowledge base as retrieval
  context — a real RAG pipeline: embed the query, pull top-k relevant past turns/entities from pgvector,
  inject as context before the LLM call. `brain/requirements.txt` doesn't have an embedding model yet
  (`sentence-transformers` per the original notes, or another local option) and Postgres doesn't have
  `pgvector` enabled yet either — both prerequisites for this.

**Sequencing note carried over from the original notes:** build the memory graph (§C1) before this,
same "build the foundation before the things that assume it exists" rule as always — the portal's RAG
chat and the knowledge-graph view are both consumers of that graph, not substitutes for building it.

---

## Architecture, reaffirmed

Go: Pico connection only — WebSocket relay, session/state tracking, offloading everything else to Python.
Python (`brain/`, soon `server/python/`): all the heavy lifting — STT/NLP/LLM/TTS, the knowledge base,
RAG, and (per this doc) the ambient-capture post-processing and the portal itself.

None of this is built. Hardware wiring is next; this document is the queue for after.
