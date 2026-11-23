"""Proposal orchestrator: draft a structured outline from retrieved evidence.

Each section lists the documents it rests on, so a human can check the
draft before it goes out. The draft is a starting point, not a finished
proposal.
"""
from __future__ import annotations

from dataclasses import dataclass

from .ingest import Index
from .retrieve import retrieve

SECTIONS = [
    ("Executive summary", "What we propose and why we are the right team."),
    ("Approach", "How the work will be delivered, step by step."),
    ("Relevant experience", "Past work that proves we can do this."),
    ("Team", "Who will do the work and what they bring."),
    ("Timeline", "Phases and milestones."),
]


@dataclass
class ProposalSection:
    heading: str
    text: str
    evidence: list[str]


def draft_proposal(index: Index, scope: str) -> list[ProposalSection]:
    parents = [p for p in retrieve(index, scope, top_k_chunks=12, top_n_parents=4)
               if p.score >= 2.0]
    evidence = [p.title for p in parents]
    passages = []
    for p in parents:
        passages.extend(p.chunks[:1])
    sections = []
    for heading, brief in SECTIONS:
        if heading == "Relevant experience" and parents:
            text = (f"{brief} Drawn from: " +
                    "; ".join(p.title for p in parents) + ".")
        elif passages:
            text = f"{brief} Supported by: {passages[0][:200].strip()}..."
        else:
            text = f"{brief} (No retrieved evidence — needs a human to fill in.)"
        sections.append(ProposalSection(heading=heading, text=text,
                                        evidence=evidence))
    return sections
