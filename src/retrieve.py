"""Parent-document retrieval + reranking.

First pass: match child chunks by term overlap (cheap). Second pass: map
children to parents, rerank parents by evidence strength + title match,
return the top parents with their best chunks.
"""
from __future__ import annotations

from dataclasses import dataclass

from .ingest import Index, tokenize


@dataclass
class RetrievedParent:
    doc_id: str
    title: str
    score: float
    chunks: list[str]


def _chunk_scores(index: Index, query_terms: list[str]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for term in query_terms:
        for chunk_id in index.postings.get(term, set()):
            chunk = index.chunks[chunk_id]
            # term frequency within the chunk, normalised by chunk length
            tf = chunk.text.lower().count(term) / max(len(chunk.text.split()), 1)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 + tf
    return scores


def retrieve(index: Index, query: str, top_k_chunks: int = 10,
             top_n_parents: int = 3) -> list[RetrievedParent]:
    query_terms = tokenize(query)
    if not query_terms:
        return []
    chunk_scores = _chunk_scores(index, query_terms)
    if not chunk_scores:
        return []
    # Map children to parents, keeping each parent's best chunks.
    parents: dict[str, dict] = {}
    for chunk_id, score in sorted(chunk_scores.items(),
                                  key=lambda kv: -kv[1])[:top_k_chunks]:
        chunk = index.chunks[chunk_id]
        entry = parents.setdefault(chunk.doc_id, {"score": 0.0, "chunks": []})
        entry["score"] += score
        entry["chunks"].append((score, chunk.text))
    # Rerank: evidence strength + a title-match bonus.
    ranked = []
    for doc_id, entry in parents.items():
        doc = index.documents[doc_id]
        title_terms = set(tokenize(doc.title))
        title_bonus = 2.0 * len(set(query_terms) & title_terms)
        ranked.append(RetrievedParent(
            doc_id=doc_id, title=doc.title,
            score=entry["score"] + title_bonus,
            chunks=[text for _, text in sorted(entry["chunks"],
                                               key=lambda c: -c[0])]))
    ranked.sort(key=lambda p: -p.score)
    return ranked[:top_n_parents]
