from .models import Evidence


class Reranker:
    name = "abstract"

    def rerank(self, query: str, evidence: list[Evidence]) -> list[Evidence]:
        raise NotImplementedError


class NoopReranker(Reranker):
    """Explicitly disabled reranker; preserves RRF order until a real adapter exists."""

    name = "disabled"

    def rerank(self, query: str, evidence: list[Evidence]) -> list[Evidence]:
        return evidence
