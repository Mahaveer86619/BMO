from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Common interface every LLM backend implements, so the router — and the
    Go hub calling /internal/chat — never need to know whether a tier is local
    Ollama or a cloud API. See notes/Software.md#Model Router."""

    @abstractmethod
    def chat(self, messages: list[dict[str, str]]) -> str:
        """messages: [{"role": "system"|"user"|"assistant", "content": "..."}]"""
        raise NotImplementedError
