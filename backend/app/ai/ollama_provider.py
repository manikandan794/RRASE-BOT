"""
Ollama provider - the PRIMARY AI backend. Runs locally/self-hosted, so no
student data ever leaves the college's own server for normal chat traffic.
"""
import logging

import httpx

from app.ai.base import AIProvider, AIProviderError, AIResponse
from app.ai.prompts import build_prompt
from app.config import get_settings

logger = logging.getLogger("rrase_college_ai.ai.ollama")


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_MODEL
        self.embed_model = settings.OLLAMA_EMBED_MODEL
        self.timeout = settings.AI_REQUEST_TIMEOUT_SECONDS

    def is_configured(self) -> bool:
        return bool(self.base_url and self.model)

    def generate(self, prompt: str, context: str | None = None) -> AIResponse:
        full_prompt = build_prompt(prompt, context or "")
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.model, "prompt": full_prompt, "stream": False},
                )
                resp.raise_for_status()
                data = resp.json()
                text = (data.get("response") or "").strip()
                if not text:
                    raise AIProviderError("Ollama returned an empty response.")
                return AIResponse(text=text, provider=self.name, model=self.model)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Ollama generate() failed: %s", exc)
            raise AIProviderError(str(exc)) from exc

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        try:
            with httpx.Client(timeout=self.timeout) as client:
                for text in texts:
                    resp = client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": self.embed_model, "prompt": text},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    vector = data.get("embedding")
                    if not vector:
                        raise AIProviderError("Ollama returned no embedding vector.")
                    vectors.append(vector)
            return vectors
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Ollama embed() failed: %s", exc)
            raise AIProviderError(str(exc)) from exc
