-- BMO brain database schema
-- Applied automatically on startup via db/client.py (_apply_schema).
-- Keep this file in sync with _apply_schema for reference / manual migrations.

CREATE TABLE IF NOT EXISTS reminders (
    id          SERIAL      PRIMARY KEY,
    text        TEXT        NOT NULL,
    when_text   TEXT,                          -- natural-language "when" from the user
    remind_at   TIMESTAMPTZ,                   -- parsed timestamp (NULL until NLP parses it)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered   BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS bots (
    id            SERIAL       PRIMARY KEY,
    name          VARCHAR(100) NOT NULL UNIQUE,  -- human-readable label e.g. "desk-bmo"
    ip_address    TEXT         NOT NULL,          -- IP the Pico W connected from
    port          INTEGER      NOT NULL DEFAULT 8080,
    active        BOOLEAN      NOT NULL DEFAULT TRUE,  -- inactive bots ignore voice input
    wake_word     VARCHAR(50),                    -- per-bot override; NULL = server default
    last_seen     TIMESTAMPTZ,                    -- last heartbeat/state message received
    registered_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS interactions (
    id           SERIAL       PRIMARY KEY,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    transcript   TEXT,                          -- what the user said (STT output)
    command      VARCHAR(50),                   -- routed command (time/search/llm/…)
    payload      TEXT,                          -- stripped text sent to handler
    reply        TEXT,                          -- final text sent to TTS
    audio_key    TEXT,                          -- MinIO object key for the response WAV
    latency_ms   INTEGER,                       -- ms from audio received to reply ready
    tts_provider VARCHAR(20)                    -- piper | xtts
);
