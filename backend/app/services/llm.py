from abc import ABC, abstractmethod
from math import isfinite

import httpx

from app.core.config import Settings


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, instruction: str, content: str) -> str | None:
        """Generate a constrained suggestion from local data."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]] | None:
        """Embed text locally when an embedding model is available."""


class OllamaProvider(LLMProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    def call(self, endpoint: str, values: dict) -> dict:
        try:
            with httpx.Client(timeout=20, trust_env=False, follow_redirects=False) as client:
                response = client.post(f"{self.settings.ollama_url}/api/{endpoint}", json=values)
                response.raise_for_status()
                payload = response.json()
                return payload if isinstance(payload, dict) else {}
        except (httpx.HTTPError, ValueError):
            return {}

    def generate(self, instruction: str, content: str) -> str | None:
        if not self.settings.ollama_model:
            return None
        result = self.call(
            "chat",
            {
                "model": self.settings.ollama_model,
                "stream": False,
                "options": {"temperature": 0, "num_predict": 300},
                "messages": [
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": content},
                ],
            },
        ).get("message")
        if isinstance(result, dict) and isinstance(result.get("content"), str):
            text = result["content"].strip()
            return text[:2000] or None
        return None

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        if not self.settings.embedding_model:
            return None
        values = self.call("embed", {"model": self.settings.embedding_model, "input": texts})
        vectors = values.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            return None
        if not all(
            isinstance(vector, list) and len(vector) == 768
            and all(isinstance(n, (int, float)) and isfinite(n) for n in vector)
            and any(vector)
            for vector in vectors
        ):
            return None
        return vectors
