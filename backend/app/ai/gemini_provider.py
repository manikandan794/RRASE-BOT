"""
Gemini provider - OPTIONAL FALLBACK, only used when Ollama is unavailable
and a GEMINI_API_KEY has been configured by the admin.
"""
import logging

import httpx

from app.ai.base import AIProvider, AIProviderError, AIResponse
from app.ai.prompts import build_prompt
from app.config import get_settings

logger = logging.getLogger("rrase_college_ai.ai.gemini")

GEMINI_API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.timeout = settings.AI_REQUEST_TIMEOUT_SECONDS

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, context: str | None = None) -> AIResponse:
        if not self.is_configured():
            raise AIProviderError("Gemini API key is not configured.")
        full_prompt = build_prompt(prompt, context or "")
        url = f"{GEMINI_API_ROOT}/{self.model}:generateContent?key={self.api_key}"
        body = {"contents": [{"parts": [{"text": full_prompt}]}]}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=body)
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates") or []
                if not candidates:
                    raise AIProviderError("Gemini returned no candidates.")
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts).strip()
                if not text:
                    raise AIProviderError("Gemini returned an empty response.")
                return AIResponse(text=text, provider=self.name, model=self.model)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("Gemini generate() failed: %s", exc)
            raise AIProviderError(str(exc)) from exc

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.is_configured():
            raise AIProviderError("Gemini API key is not configured.")
        url = f"{GEMINI_API_ROOT}/embedding-001:batchEmbedContents?key={self.api_key}"
        requests = [{"model": "models/embedding-001", "content": {"parts": [{"text": t}]}} for t in texts]
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json={"requests": requests})
                resp.raise_for_status()
                data = resp.json()
                embeddings = data.get("embeddings") or []
                return [e["values"] for e in embeddings]
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("Gemini embed() failed: %s", exc)
            raise AIProviderError(str(exc)) from exc
