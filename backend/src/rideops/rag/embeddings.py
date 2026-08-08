import math
import re
import hashlib
from collections.abc import Sequence


class EmbeddingModel:
    """Small deterministic local embedding interface; replaceable by an API adapter later."""

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class MockEmbedding(EmbeddingModel):
    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    @staticmethod
    def _tokens(text: str) -> list[str]:
        # CJK characters make the mock useful for Chinese policies; words cover English too.
        return re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9_]+", text.lower())

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in self._tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            vector[int.from_bytes(digest[:4], "big") % self.dimensions] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right))))
