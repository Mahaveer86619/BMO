from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .base import LLMProvider

_ROLE_TO_MESSAGE: dict[str, type[BaseMessage]] = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
}


class APIProvider(LLMProvider):
    """Any OpenAI-compatible endpoint (OpenRouter, Groq, Together, a local vLLM
    server, ...) via a configurable base_url — ChatOpenAI's `base_url`/`api_key`
    aren't OpenAI-specific, they're just "an OpenAI-shaped HTTP API". For a
    provider with a genuinely different wire format (e.g. Anthropic's native
    API), swap this class for langchain_anthropic.ChatAnthropic behind the same
    LLMProvider interface — nothing else in the router or Go side changes.

    Only ever constructed when LLM_PROVIDER_CLOUD_ENABLED=true — see
    notes/Software.md's data-boundary rule and app/llm/router.py."""

    def __init__(self, model: str, base_url: str, api_key: str, temperature: float = 0.7):
        self._llm = ChatOpenAI(model=model, base_url=base_url, api_key=api_key, temperature=temperature)

    def chat(self, messages: list[dict[str, str]]) -> str:
        lc_messages = [_ROLE_TO_MESSAGE[m["role"]](content=m["content"]) for m in messages]
        response = self._llm.invoke(lc_messages)
        return str(response.content)
