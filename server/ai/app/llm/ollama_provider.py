from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from .base import LLMProvider

_ROLE_TO_MESSAGE: dict[str, type[BaseMessage]] = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
}


class OllamaProvider(LLMProvider):
    """Local Ollama models — the default tier. Ollama runs natively on the host
    in local dev (see notes/Software.md#Docker Setup); base_url must resolve
    from inside the container in production (see server/docker-compose.yml)."""

    def __init__(self, model: str, base_url: str, temperature: float = 0.7):
        self._llm = ChatOllama(model=model, base_url=base_url, temperature=temperature)

    def chat(self, messages: list[dict[str, str]]) -> str:
        lc_messages = [_ROLE_TO_MESSAGE[m["role"]](content=m["content"]) for m in messages]
        response = self._llm.invoke(lc_messages)
        return str(response.content)
