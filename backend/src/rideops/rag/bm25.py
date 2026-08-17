import math
import re
from collections import Counter

import jieba


def tokenize(text: str) -> list[str]:
    """Chinese-aware tokens plus IDs, dates, amounts and English abbreviations."""
    special = re.findall(r"[A-Za-z]+[-_]?[A-Za-z0-9]+|\d+(?:\.\d+)?%?|\d{4}[-年/]\d{1,2}(?:[-月/]\d{1,2})?", text)
    normalized = [token.lower() for token in jieba.lcut(text, cut_all=False) if token.strip()]
    normalized.extend(token.lower() for token in special)
    return normalized


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.document_ids: list[str] = []
        self.documents: list[list[str]] = []
        self.term_frequency: list[Counter[str]] = []
        self.document_frequency: Counter[str] = Counter()
        self.average_document_length = 0.0

    def add(self, document_id: str, content: str) -> None:
        tokens = tokenize(content)
        self.document_ids.append(document_id)
        self.documents.append(tokens)
        self.term_frequency.append(Counter(tokens))
        self.document_frequency.update(set(tokens))
        self.average_document_length = sum(len(item) for item in self.documents) / len(self.documents)

    def search(self, query: str, top_k: int = 20) -> list[tuple[str, float]]:
        query_terms = set(tokenize(query))
        total_documents = len(self.documents)
        scores: list[tuple[str, float]] = []
        for index, frequencies in enumerate(self.term_frequency):
            length = len(self.documents[index]) or 1
            score = 0.0
            matched_terms = 0
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                matched_terms += 1
                document_frequency = self.document_frequency[term]
                idf = math.log(1 + (total_documents - document_frequency + 0.5) / (document_frequency + 0.5))
                denominator = frequency + self.k1 * (1 - self.b + self.b * length / max(self.average_document_length, 1))
                score += idf * frequency * (self.k1 + 1) / denominator
            coverage = matched_terms / max(len(query_terms), 1)
            scores.append((self.document_ids[index], score if coverage >= 0.5 else 0.0))
        scores.sort(key=lambda item: item[1], reverse=True)
        return [(document_id, score) for document_id, score in scores[:top_k] if score > 0]
