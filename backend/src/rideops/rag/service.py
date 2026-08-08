from pathlib import Path

from .models import RAGResponse
from .parser import load_markdown_documents
from .retriever import InMemoryRetriever


class RAGService:
    def __init__(self, retriever: InMemoryRetriever) -> None:
        self.retriever = retriever

    def query(self, query: str, top_k: int = 3, min_score: float = 0.18) -> RAGResponse:
        evidence = self.retriever.search(query, top_k=top_k, min_score=min_score)
        if not evidence:
            return RAGResponse(query=query, answerable=False, evidence=[], refusal_reason="未检索到足够的政策证据，无法可靠回答。")
        return RAGResponse(query=query, answerable=True, evidence=evidence)


def build_default_service(documents_dir: Path) -> RAGService:
    retriever = InMemoryRetriever()
    retriever.add_documents(load_markdown_documents(documents_dir))
    return RAGService(retriever)
