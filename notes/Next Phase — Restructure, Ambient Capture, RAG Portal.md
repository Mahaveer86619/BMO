---
project: "[[Custom BMO – Desk AI Bot]]"
tags:
  - bmo
  - roadmap
  - planning
status: Planned — not started
last_updated: 2026-08-30
---
> Captured 2026-08-30 so this doesn't get lost — hardware wiring is the immediate focus (jumper wires,
> no soldering); this is the software work queued up for after that. Nothing below is built yet.

---

## 1. Directory restructure — one `server/` with a subdir per concern

Current layout has `server/` (Go), `brain/` (Python), plus root-level `Dockerfile`/`docker-compose*.yml`/
`supervisord.conf`/`docker/` that span both. Target:

```
server/
  golang/           <- today's server/ (cmd/, internal/, go.mod, go.sum, standalone Dockerfile)
  python/           <- today's brain/ (app/, static/, entrypoint.sh, requirements.txt, Dockerfile)
  ollama/           <- Ollama-specific config/scripts (vendoring itself still happens in the root Dockerfile)
  postgres/         <- schema reference, init scripts
  redis/            <- config, if any ever needed
  storage/          <- local object storage — a bind-mounted directory on disk, not a MinIO named
                       volume, so stored audio is directly browsable/backupable from the host
  Dockerfile              <- single-image monolith (moved from root)
  docker-compose.yml       <- single-image variant (moved from root)
  docker-compose.multi.yml <- multi-image variant (moved from root)
  supervisord.conf
  docker/entrypoint.sh, bootstrap.sh
```

Mechanically low-risk (Go's module path doesn't care about directory nesting, only import paths relative
to `go.mod`'s location — as long as `cmd/`/`internal/` stay direct children of wherever `go.mod` lands).
The real work is updating every `COPY`/`build: context:`/volume path across both Dockerfiles and both
compose files to match, plus retesting both topologies end-to-end. Not done in this session — deferred
per your call to focus on hardware first.

**Open question for when this happens:** MinIO vs. plain bind-mounted local storage for `server/storage/`
— you said "a dedicated dir mounted volume for a local object storage," which reads as **drop MinIO,
use a plain directory** rather than keep the S3-compatible layer. Worth confirming — MinIO's `mc`/S3 API
is convenient for `brain/`'s existing `core/storage.py`, but a flat directory is simpler to inspect by hand
and matches "local server, local hardware" more literally. Either way `core/storage.py`'s
`upload_audio()`/interface stays the seam — swapping the backend shouldn't touch callers.

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
