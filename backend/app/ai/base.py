"""
AI Provider Interface.

Every AI backend (Ollama, Gemini, and any future provider) implements this
interface so the rest of the application never depends on a specific
vendor SDK.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AIResponse:
    text: str
    provider: str
    model: str


class AIProviderError(Exception):
    """Raised when a provider is unreachable or errors out. The provider
    manager catches this and falls through to the next provider."""


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """Cheap check - e.g. an API key is present, a base URL is set."""

    @abstractmethod
    def generate(self, prompt: str, context: str | None = None) -> AIResponse:
        """Generate a grounded answer. Must raise AIProviderError on failure,
        never return a fabricated answer when it cannot reach the model."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
