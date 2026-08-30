from functools import lru_cache
from typing import Literal

from ..config import settings
from .api_provider import APIProvider
from .base import LLMProvider
from .ollama_provider import OllamaProvider

Tier = Literal["fast", "reasoning", "cloud"]


@lru_cache(maxsize=None)
def get_provider(tier: Tier = "fast") -> LLMProvider:
    """Three tiers, cheapest-first — see notes/Software.md#Model Router.

    This only resolves an already-chosen tier name to a live provider instance
    (and caches it — provider objects hold a live client, no need to rebuild
    per request). *Deciding* which tier a given query needs — NLP fast-path vs
    1b vs 3b+tools vs cloud — is intent-classification logic that doesn't exist
    yet (Topic C3 in BMO – Capability Topics.md); callers currently pass the
    tier explicitly."""
    if tier == "cloud":
        if not settings.llm_provider_cloud_enabled:
            raise RuntimeError(
                "Cloud LLM escalation is disabled (LLM_PROVIDER_CLOUD_ENABLED=false). "
                "This must stay an explicit, logged opt-in — see the data-boundary rule "
                "in notes/Software.md and notes/Custom BMO – Desk AI Bot.md."
            )
        return APIProvider(
            model=settings.cloud_model,
            base_url=settings.cloud_api_base_url,
            api_key=settings.cloud_api_key,
        )

    model = settings.ollama_reasoning_model if tier == "reasoning" else settings.ollama_fast_model
    return OllamaProvider(model=model, base_url=settings.ollama_base_url)
