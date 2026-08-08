import re
from dataclasses import dataclass

from .parser import PolicyDocument


@dataclass(frozen=True)
class DocumentChunk:
    document_id: str
    title: str
    section: str
    content: str
    source: str


def split_markdown(document: PolicyDocument, max_chars: int = 420) -> list[DocumentChunk]:
    """Split by Markdown sections first, then by size while keeping section names."""
    sections = re.split(r"(?=^##\s+)", document.content, flags=re.MULTILINE)
    chunks: list[DocumentChunk] = []
    for raw_section in sections:
        raw_section = raw_section.strip()
        if not raw_section:
            continue
        heading_match = re.match(r"^##\s+(.+)$", raw_section, re.MULTILINE)
        # A document title/front matter is metadata, not a retrievable policy section.
        if not heading_match and raw_section.startswith("#"):
            continue
        section = heading_match.group(1).strip() if heading_match else "overview"
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", raw_section) if part.strip()]
        current = ""
        for paragraph in paragraphs:
            if current and len(current) + len(paragraph) + 2 > max_chars:
                chunks.append(DocumentChunk(document.document_id, document.title, section, current, document.source))
                current = ""
            current = f"{current}\n\n{paragraph}".strip()
        if current:
            chunks.append(DocumentChunk(document.document_id, document.title, section, current, document.source))
    return chunks
