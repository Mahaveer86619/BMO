from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    """Env-driven config for the AI service. Field names map to SCREAMING_SNAKE_CASE
    env vars (e.g. ollama_base_url -> OLLAMA_BASE_URL) to match the Go side's
    convention in internal/config/config.go."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ai_host: str = "127.0.0.1"
    ai_port: int = 8500

    # Data-boundary rule (notes/Software.md, notes/Custom BMO – Desk AI Bot.md):
    # cloud escalation must always be an explicit, logged opt-in — never a silent default.
    llm_provider_cloud_enabled: bool = False

    ollama_base_url: str = "http://localhost:11434"
    ollama_fast_model: str = "llama3.2:1b"
    ollama_reasoning_model: str = "llama3.2:3b"

    cloud_api_base_url: str = "https://api.openai.com/v1"
    cloud_api_key: str = ""
    cloud_model: str = "gpt-4o-mini"

    # "" = auto-detect (see app/compute.py). Set to "cpu" or "cuda" to force one.
    compute_mode_override: str = ""


settings = AISettings()
