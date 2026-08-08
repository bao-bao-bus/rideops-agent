import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PolicyDocument:
    document_id: str
    title: str
    source: str
    content: str


def parse_markdown(path: Path) -> PolicyDocument:
    """Read a local Markdown policy and preserve its source for citations."""
    content = path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else path.stem
    return PolicyDocument(document_id=path.stem, title=title, source=str(path), content=content)


def load_markdown_documents(directory: Path) -> list[PolicyDocument]:
    return [parse_markdown(path) for path in sorted(Path(directory).glob("*.md"))]
