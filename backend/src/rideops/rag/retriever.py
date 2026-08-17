from dataclasses import dataclass

from .bm25 import BM25Index
from .chunker import DocumentChunk, split_markdown
from .embeddings import EmbeddingProvider, MockEmbeddingProvider
from .models import Evidence
from .parser import PolicyDocument
from .reranker import NoopReranker, Reranker
from .vector_store import SQLiteVectorStore, chunk_id_for


@dataclass(frozen=True)
class RRFConfig:
    candidate_k: int = 20
    fusion_k: int = 60
    final_k: int = 10
    min_vector_similarity: float = 0.25


class HybridRetriever:
    def __init__(self, index_path, embedding_provider: EmbeddingProvider | None = None, rrf: RRFConfig | None = None, reranker: Reranker | None = None) -> None:
        self.embedding_provider = embedding_provider or MockEmbeddingProvider()
        self.vector_store = SQLiteVectorStore(index_path)
        self.rrf = rrf or RRFConfig()
        self.reranker = reranker or NoopReranker()
        self.bm25 = BM25Index()

    def add_documents(self, documents: list[PolicyDocument]) -> None:
        chunks = [chunk for document in documents for chunk in split_markdown(document)]
        self.vector_store.sync(chunks, self.embedding_provider)
        self.bm25 = BM25Index()
        for chunk in chunks:
            self.bm25.add(chunk_id_for(chunk), chunk.content)

    def search(self, query: str, top_k: int = 3, min_score: float = 0.18) -> list[Evidence]:
        query_embedding = self.embedding_provider.embed_query(query)
        keyword_results = self.bm25.search(query, self.rrf.candidate_k)
        vector_results = [item for item in self.vector_store.search(query_embedding, self.rrf.candidate_k) if item[1] >= self.rrf.min_vector_similarity]
        fused: dict[str, float] = {}
        for rank, (chunk_id, _) in enumerate(keyword_results, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1 / (self.rrf.fusion_k + rank)
        for rank, (chunk_id, _) in enumerate(vector_results, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1 / (self.rrf.fusion_k + rank)
        ranked = sorted(fused.items(), key=lambda item: item[1], reverse=True)[: max(top_k, self.rrf.final_k)]
        if not ranked:
            return []
        max_score = ranked[0][1]
        evidence: list[Evidence] = []
        for chunk_id, score in ranked:
            normalized_score = score / max_score if max_score else 0.0
            if normalized_score < min_score:
                continue
            stored = self.vector_store.get(chunk_id)
            if stored is None:
                continue
            evidence.append(Evidence(document_id=stored.chunk.document_id, title=stored.chunk.title, section=stored.chunk.section, content=stored.chunk.content, score=round(normalized_score, 4), source=stored.chunk.source))
            if len(evidence) >= top_k:
                break
        return self.reranker.rerank(query, evidence)


# Kept as a small compatibility alias for callers of the first prototype.
InMemoryRetriever = HybridRetriever
