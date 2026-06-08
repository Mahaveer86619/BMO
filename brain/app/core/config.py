from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "BMO Server"
    PORT: int = 8000

    # LLM
    OLLAMA_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"

    # STT — "local" uses faster-whisper (CPU, int8), "huggingface" calls HF Inference API
    STT_PROVIDER: str = "local"
    WHISPER_MODEL: str = "base"
    WHISPER_MODEL_CACHE: str = "/app/data/whisper"

    # HuggingFace (only needed when STT_PROVIDER=huggingface)
    HF_API_TOKEN: str = ""
    HF_WHISPER_MODEL: str = "openai/whisper-base"

    # TTS
    PIPER_MODEL_PATH: str = "/app/data/piper/en_GB-alan-low.onnx"

settings = Settings()
