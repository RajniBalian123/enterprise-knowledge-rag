"""Scheduler worker: periodic sync from sources.

The worker is separate from the API, so a slow source never blocks a
question. It records what it ingested, so a re-run only picks up new or
changed documents.
"""
from __future__ import annotations

from pathlib import Path

from .ingest import Index


class Worker:
    def __init__(self, index: Index):
        self.index = index
        self.runs: list[dict] = []

    def sync(self, directory: Path, source: str = "files") -> dict:
        before_chunks = len(self.index.chunks)
        before_docs = len(self.index.documents)
        added = self.index.load_directory(directory, source)
        run = {
            "source": source,
            "new_chunks": len(self.index.chunks) - before_chunks,
            "total_docs": len(self.index.documents),
            "total_chunks": len(self.index.chunks),
            "docs_added_or_changed": added,
        }
        self.runs.append(run)
        return run
