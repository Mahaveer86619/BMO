from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "BMO Server"
    PORT: int = 8000

    # LLM
    OLLAMA_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"

    # STT — "local" uses faster-whisper (CPU, int8), "huggingface" calls HF Inference API
    STT_PROVIDER: str = "local"
    WHISPER_MODEL: str = "base"
    WHISPER_MODEL_CACHE: str = "/app/data/whisper"

    # HuggingFace (only needed when STT_PROVIDER=huggingface)
    HF_API_TOKEN: str = ""
    HF_WHISPER_MODEL: str = "openai/whisper-base"

    # TTS — "piper" is fast/generic, "xtts" clones the BMO reference voice
    TTS_PROVIDER: str = "piper"
    PIPER_MODEL_PATH: str = "/opt/piper-models/en_GB-alan-low.onnx"
    XTTS_REFERENCE_AUDIO: str = "/app/data/bmo_voice/reference.wav"
    XTTS_CACHE_DIR: str = "/app/data/xtts"

    # Database (PostgreSQL via asyncpg) — leave empty to disable DB features
    DATABASE_URL: str = ""

    # Default city used by the weather tool when no location is specified
    DEFAULT_WEATHER_LOCATION: str = "London"

    # Wake word — set to a word (e.g. "lumi") to require it before processing.
    # Leave empty to disable (useful for HTTP /talk testing).
    WAKE_WORD: str = ""

    # MinIO / S3-compatible object storage for audio files
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "bmo"
    MINIO_SECRET_KEY: str = "bmo_secret"
    MINIO_BUCKET: str = "bmo-audio"
    MINIO_SECURE: bool = False

    # Logging verbosity: dev | verbose | alerts | ignore
    LOG_LEVEL: str = "alerts"

settings = Settings()
