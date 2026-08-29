"""
Provider Manager - implements the fallback chain:

    Ollama (primary) -> Gemini (optional fallback) -> None

The chat service is responsible for what happens when this returns None
(database/FAQ answers where possible, otherwise "information unavailable").
Adding a future provider means writing one more AIProvider subclass and
appending it to `_load_providers()` - nothing else in the app changes.
"""
import logging

from app.ai.base import AIProvider, AIProviderError, AIResponse
from app.ai.gemini_provider import GeminiProvider
from app.ai.ollama_provider import OllamaProvider

logger = logging.getLogger("rrase_college_ai.ai.manager")


class ProviderManager:
    def __init__(self, providers: list[AIProvider] | None = None) -> None:
        self.providers = providers if providers is not None else self._load_providers()

    @staticmethod
    def _load_providers() -> list[AIProvider]:
        # Order matters: Ollama is always tried first (primary), Gemini second
        # (optional fallback). Future providers append here.
        return [OllamaProvider(), GeminiProvider()]

    def generate(self, prompt: str, context: str | None = None) -> AIResponse | None:
        for provider in self.providers:
            if not provider.is_configured():
                continue
            try:
                return provider.generate(prompt, context)
            except AIProviderError as exc:
                logger.info("Provider %s unavailable, trying next: %s", provider.name, exc)
                continue
        return None

    def embed(self, texts: list[str]) -> tuple[list[list[float]], str] | None:
        """Returns (vectors, provider_name) or None if no embedding backend
        is reachable. Embedding backend follows the same fallback order as
        generation, so retrieval never depends on a second, separately
        configured system."""
        for provider in self.providers:
            if not provider.is_configured():
                continue
            try:
                return provider.embed(texts), provider.name
            except AIProviderError as exc:
                logger.info("Embedding via %s failed, trying next: %s", provider.name, exc)
                continue
        return None


_manager: ProviderManager | None = None


def get_provider_manager() -> ProviderManager:
    global _manager
    if _manager is None:
        _manager = ProviderManager()
    return _manager
