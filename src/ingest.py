"""Ingestion: connectors, chunking, parent registry, idempotent indexing.

Each document gets a stable ID (source + path). Re-ingesting the same
document creates no duplicate chunks; a changed document replaces its
chunks.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

CHUNK_SIZE = 600
CHUNK_OVERLAP = 100

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "by", "at", "as", "it", "its", "this",
    "that", "from", "we", "our", "you", "your", "can", "will", "has", "have",
}


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower())
            if t not in STOPWORDS]


@dataclass
class Document:
    doc_id: str
    title: str
    source: str
    text: str


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    text: str


def chunk_text(text: str) -> list[str]:
    """Paragraph-aware chunks of ~CHUNK_SIZE chars with overlap."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        if current and len(current) + len(para) + 1 > CHUNK_SIZE:
            chunks.append(current)
            current = current[-CHUNK_OVERLAP:] if len(current) > CHUNK_OVERLAP else current
            current = (current + "\n" + para).strip() if current else para
        else:
            current = (current + "\n" + para).strip() if current else para
    if current:
        chunks.append(current)
    return chunks


class Index:
    """Inverted index: term -> chunk ids. Plus the parent registry."""

    def __init__(self):
        self.documents: dict[str, Document] = {}
        self.chunks: dict[str, Chunk] = {}
        self.postings: dict[str, set[str]] = {}
        self._doc_hashes: dict[str, str] = {}

    def ingest(self, doc: Document) -> int:
        """Index a document. Returns the number of NEW chunks added.
        Re-ingesting an unchanged document adds zero."""
        digest = hashlib.sha256(doc.text.encode()).hexdigest()
        if self._doc_hashes.get(doc.doc_id) == digest:
            return 0
        self._remove_doc(doc.doc_id)
        self.documents[doc.doc_id] = doc
        self._doc_hashes[doc.doc_id] = digest
        added = 0
        for i, text in enumerate(chunk_text(doc.text)):
            chunk_id = f"{doc.doc_id}#c{i}"
            self.chunks[chunk_id] = Chunk(chunk_id, doc.doc_id, text)
            for term in set(tokenize(text)):
                self.postings.setdefault(term, set()).add(chunk_id)
            added += 1
        return added

    def _remove_doc(self, doc_id: str) -> None:
        for chunk_id in [c for c, ch in self.chunks.items()
                         if ch.doc_id == doc_id]:
            for term in set(tokenize(self.chunks[chunk_id].text)):
                self.postings.get(term, set()).discard(chunk_id)
            del self.chunks[chunk_id]
        self.documents.pop(doc_id, None)

    def load_directory(self, directory: Path, source: str = "files") -> int:
        total = 0
        for path in sorted(directory.glob("*.txt")):
            title = path.stem.replace("_", " ").title()
            total += self.ingest(Document(
                doc_id=f"{source}:{path.name}", title=title,
                source=source, text=path.read_text(encoding="utf-8")))
        return total
