import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .chunker import DocumentChunk
from .embeddings import EmbeddingProvider, cosine_similarity


@dataclass(frozen=True)
class StoredChunk:
    chunk_id: str
    chunk: DocumentChunk
    embedding: list[float]
    embedding_model: str


def chunk_id_for(chunk: DocumentChunk) -> str:
    digest = hashlib.sha256(f"{chunk.document_id}:{chunk.section}:{chunk.content}".encode("utf-8")).hexdigest()[:16]
    return f"{chunk.document_id}:{digest}"


class SQLiteVectorStore:
    """Persistent local vector store. It keeps the same adapter boundary as Milvus later."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS rag_chunks (chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, title TEXT NOT NULL, section TEXT NOT NULL, content TEXT NOT NULL, source TEXT NOT NULL, content_hash TEXT NOT NULL, embedding_model TEXT NOT NULL, embedding_json TEXT NOT NULL)")

    def _records(self) -> list[StoredChunk]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute("SELECT * FROM rag_chunks ORDER BY chunk_id").fetchall()
        return [StoredChunk(row[0], DocumentChunk(row[1], row[2], row[3], row[4], row[5]), json.loads(row[8]), row[7]) for row in rows]

    def sync(self, chunks: list[DocumentChunk], provider: EmbeddingProvider) -> None:
        expected = {chunk_id_for(chunk): chunk for chunk in chunks}
        current = {record.chunk_id: record for record in self._records()}
        model = provider.model_name
        current_matches = len(current) == len(expected) and all(
            chunk_id in current and current[chunk_id].embedding_model == model and current[chunk_id].chunk.content == chunk.content
            for chunk_id, chunk in expected.items()
        )
        if current_matches:
            return
        embeddings = provider.embed_documents([chunk.content for chunk in chunks])
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("DELETE FROM rag_chunks")
            connection.executemany(
                "INSERT INTO rag_chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (chunk_id_for(chunk), chunk.document_id, chunk.title, chunk.section, chunk.content, chunk.source, hashlib.sha256(chunk.content.encode("utf-8")).hexdigest(), model, json.dumps(embedding))
                    for chunk, embedding in zip(chunks, embeddings)
                ],
            )

    def search(self, query_embedding: list[float], top_k: int = 20) -> list[tuple[str, float]]:
        scored = [(record.chunk_id, cosine_similarity(query_embedding, record.embedding)) for record in self._records()]
        scored.sort(key=lambda item: item[1], reverse=True)
        return [(chunk_id, score) for chunk_id, score in scored[:top_k] if score > 0]

    def get(self, chunk_id: str) -> StoredChunk | None:
        return next((record for record in self._records() if record.chunk_id == chunk_id), None)

    def all(self) -> list[StoredChunk]:
        return self._records()
