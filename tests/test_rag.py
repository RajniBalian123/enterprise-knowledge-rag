"""Checks for retrieval, reranking, abstention, ingestion, proposals."""

import unittest
from pathlib import Path

from src.ingest import Document, Index
from src.proposals import draft_proposal
from src.qa import ask
from src.retrieve import retrieve
from src.worker import Worker

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "data" / "docs"


def indexed() -> Index:
    index = Index()
    index.load_directory(DOCS)
    return index


class TestRetrieval(unittest.TestCase):
    def test_question_returns_parent_document(self):
        parents = retrieve(indexed(), "confined space entry permit")
        self.assertTrue(parents)
        self.assertIn("Confined Space", parents[0].title)

    def test_rerank_prefers_title_match(self):
        # "capability statement" matches the capability doc's title, so it
        # should outrank a doc that only shares a body word.
        parents = retrieve(indexed(), "capability statement services")
        self.assertEqual(parents[0].title, "Capability Statement")

    def test_no_match_returns_nothing(self):
        self.assertEqual(retrieve(indexed(), "zzzzqqq wwwww"), [])


class TestQA(unittest.TestCase):
    def test_grounded_answer_cites_sources(self):
        answer = ask(indexed(), "What is the confined space entry procedure?")
        self.assertFalse(answer.abstained)
        self.assertTrue(answer.citations)
        self.assertIn("Confined Space", answer.citations[0])

    def test_no_source_abstains(self):
        answer = ask(indexed(), "What is the policy on interplanetary travel?")
        self.assertTrue(answer.abstained)
        self.assertEqual(answer.citations, [])


class TestIngestion(unittest.TestCase):
    def test_reingest_adds_nothing(self):
        index = indexed()
        chunks_before = len(index.chunks)
        added = index.load_directory(DOCS)
        self.assertEqual(added, 0)
        self.assertEqual(len(index.chunks), chunks_before)

    def test_changed_document_replaces_chunks(self):
        index = Index()
        doc = Document(doc_id="files:a.txt", title="A", source="files",
                       text="alpha beta gamma " * 40)
        self.assertGreater(index.ingest(doc), 0)
        chunks_before = len(index.chunks)
        doc2 = Document(doc_id="files:a.txt", title="A", source="files",
                        text="delta epsilon zeta " * 40)
        index.ingest(doc2)
        self.assertEqual(len(index.chunks), chunks_before)
        self.assertNotIn("alpha", " ".join(c.text for c in index.chunks.values()))

    def test_worker_sync_is_idempotent(self):
        index = Index()
        worker = Worker(index)
        first = worker.sync(DOCS)
        second = worker.sync(DOCS)
        self.assertEqual(second["new_chunks"], 0)
        self.assertEqual(first["total_docs"], second["total_docs"])


class TestProposals(unittest.TestCase):
    def test_outline_sections_cite_evidence(self):
        sections = draft_proposal(indexed(), "Safety audit of a power plant")
        self.assertEqual(len(sections), 5)
        headings = [s.heading for s in sections]
        self.assertIn("Relevant experience", headings)
        experience = next(s for s in sections
                          if s.heading == "Relevant experience")
        self.assertTrue(experience.evidence)
        self.assertTrue(any("Northfield" in e or "Capability" in e
                            for e in experience.evidence))


if __name__ == "__main__":
    unittest.main()
