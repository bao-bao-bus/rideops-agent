from pathlib import Path

from .models import RAGResponse
from .parser import load_markdown_documents
from .embeddings import EmbeddingProvider
from .retriever import HybridRetriever


class RAGService:
    def __init__(self, retriever: HybridRetriever) -> None:
        self.retriever = retriever

    def query(self, query: str, top_k: int = 3, min_score: float = 0.18) -> RAGResponse:
        evidence = self.retriever.search(query, top_k=top_k, min_score=min_score)
        if not evidence:
            return RAGResponse(query=query, answerable=False, evidence=[], refusal_reason="未检索到足够的政策证据，无法可靠回答。", retrieval_strategy="bm25+vector+rrf")
        return RAGResponse(query=query, answerable=True, evidence=evidence, retrieval_strategy="bm25+vector+rrf")


def build_default_service(documents_dir: Path, index_path: Path | None = None, embedding_provider: EmbeddingProvider | None = None) -> RAGService:
    if index_path is None:
        index_path = Path(documents_dir).parents[1] / "data" / "rag-index.db"
    retriever = HybridRetriever(index_path=index_path, embedding_provider=embedding_provider)
    retriever.add_documents(load_markdown_documents(documents_dir))
    return RAGService(retriever)
