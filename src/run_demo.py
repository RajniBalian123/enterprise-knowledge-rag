"""Demo walkthrough: ingest, ask, draft a proposal, run the worker sync."""

from pathlib import Path

from src.ingest import Index
from src.proposals import draft_proposal
from src.qa import ask
from src.worker import Worker

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    index = Index()
    worker = Worker(index)

    run = worker.sync(ROOT / "data" / "docs")
    print(f"1. Worker sync: {run['total_docs']} documents, "
          f"{run['total_chunks']} chunks indexed")

    # Re-sync: nothing new, nothing duplicated.
    run2 = worker.sync(ROOT / "data" / "docs")
    print(f"2. Second sync: {run2['new_chunks']} new chunks "
          f"(ingestion is idempotent)")

    question = "What is the confined space entry procedure?"
    answer = ask(index, question)
    print(f"\n3. Q: {question}")
    print(f"   A: {answer.text[:300]}")
    print(f"   Citations: {answer.citations}")

    question2 = "What is the company's policy on interplanetary travel?"
    answer2 = ask(index, question2)
    print(f"\n4. Q: {question2}")
    print(f"   A: {answer2.text} (abstained: {answer2.abstained})")

    print("\n5. Proposal outline for: 'Safety audit of the Harborview plant'")
    for section in draft_proposal(index, "Safety audit of the Harborview plant"):
        print(f"   - {section.heading}: {section.text[:120]}")
        print(f"     Evidence: {section.evidence}")


if __name__ == "__main__":
    main()
