import re
from dataclasses import dataclass

from .chunker import DocumentChunk, split_markdown
from .embeddings import EmbeddingModel, MockEmbedding, cosine_similarity
from .models import Evidence
from .parser import PolicyDocument


@dataclass(frozen=True)
class IndexedChunk:
    chunk: DocumentChunk
    embedding: list[float]


class InMemoryRetriever:
    def __init__(self, embedding_model: EmbeddingModel | None = None) -> None:
        self.embedding_model = embedding_model or MockEmbedding()
        self.chunks: list[IndexedChunk] = []

    def add_documents(self, documents: list[PolicyDocument]) -> None:
        for document in documents:
            for chunk in split_markdown(document):
                self.chunks.append(IndexedChunk(chunk, self.embedding_model.embed(chunk.content)))

    @staticmethod
    def _keyword_score(query: str, content: str) -> float:
        terms = re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9_]+", query.lower())
        if not terms:
            return 0.0
        matched = sum(1 for term in set(terms) if term in content.lower())
        return matched / len(set(terms))

    def search(self, query: str, top_k: int = 3, min_score: float = 0.0, rerank: bool = True) -> list[Evidence]:
        query_embedding = self.embedding_model.embed(query)
        scored: list[tuple[float, IndexedChunk]] = []
        for indexed in self.chunks:
            keyword = self._keyword_score(query, indexed.chunk.content)
            vector = cosine_similarity(query_embedding, indexed.embedding)
            score = (0.55 * keyword) + (0.45 * vector)
            if score >= min_score:
                scored.append((score, indexed))
        # The optional local reranker favors exact query terms without requiring a remote service.
        if rerank:
            scored.sort(key=lambda item: (item[0], self._keyword_score(query, item[1].chunk.section)), reverse=True)
        else:
            scored.sort(key=lambda item: item[0], reverse=True)
        return [
            Evidence(document_id=item.chunk.document_id, title=item.chunk.title, section=item.chunk.section,
                     content=item.chunk.content, score=round(score, 4), source=item.chunk.source)
            for score, item in scored[:top_k]
        ]
