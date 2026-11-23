"""Q&A service: retrieve, rerank, answer with citations — or abstain.

Generation here is extractive: the most relevant passages, quoted, with
citations. A language model is a plug-in point. The abstention rule is
identical either way: no grounded source, no answer.
"""
from __future__ import annotations

from dataclasses import dataclass

from .ingest import Index
from .retrieve import RetrievedParent, retrieve

MIN_SCORE = 2.0


@dataclass
class Answer:
    text: str
    citations: list[str]
    abstained: bool


def _best_passage(chunks: list[str], query_terms: list[str]) -> str:
    def score(text: str) -> int:
        lowered = text.lower()
        return sum(lowered.count(t) for t in query_terms)
    return max(chunks, key=score)


def ask(index: Index, question: str) -> Answer:
    from .ingest import tokenize
    query_terms = tokenize(question)
    # Vocabulary check: a question containing a term the corpus has never
    # seen cannot be grounded in it. Abstaining here is the conservative
    # failure mode — a wrong confident answer costs more than no answer.
    if query_terms and any(t not in index.postings for t in query_terms):
        return Answer(
            text="I don't have a grounded source for that question in the "
                 "indexed documents — it contains terms that appear in none "
                 "of them.",
            citations=[], abstained=True)
    parents = retrieve(index, question)
    if not parents or parents[0].score < MIN_SCORE:
        return Answer(
            text="I don't have a grounded source for that question in the "
                 "indexed documents.",
            citations=[], abstained=True)
    lines = []
    citations = []
    for parent in parents:
        passage = _best_passage(parent.chunks, query_terms)
        lines.append(passage.strip())
        citations.append(f"{parent.title} (score {parent.score:.1f})")
    return Answer(text="\n\n".join(lines), citations=citations, abstained=False)
