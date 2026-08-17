import hashlib
import math
import re
from collections.abc import Sequence

import httpx


class EmbeddingProvider:
    model_name = "unknown"

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic local fallback used when no real embedding credentials exist."""

    model_name = "mock-hash-256"

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9_]+", text.lower())

    def embed_query(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in self._tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            vector[int.from_bytes(digest[:4], "big") % self.dimensions] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    def embed(self, text: str) -> list[float]:
        return self.embed_query(text)


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """Adapter for OpenAI-compatible /v1/embeddings endpoints."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 30.0) -> None:
        if not base_url or not api_key:
            raise ValueError("OpenAI-compatible Embedding requires EMBEDDING_BASE_URL and EMBEDDING_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model
        self.timeout = timeout

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = httpx.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model_name, "input": texts},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        if len(data) != len(texts):
            raise ValueError("Embedding response count does not match input count")
        return [item["embedding"] for item in sorted(data, key=lambda item: item.get("index", 0))]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


# Backward-compatible names for the original local prototype.
EmbeddingModel = EmbeddingProvider
MockEmbedding = MockEmbeddingProvider


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right))))


def build_embedding_provider(settings) -> EmbeddingProvider:
    if settings.embedding_provider.lower() in {"openai", "openai-compatible", "real"}:
        return OpenAICompatibleEmbeddingProvider(settings.embedding_base_url, settings.embedding_api_key, settings.embedding_model)
    return MockEmbeddingProvider()
