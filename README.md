# Enterprise Knowledge RAG — Demo

A retrieval-augmented generation platform for enterprise document Q&A and
AI-assisted proposal drafting, rebuilt from scratch with synthetic data.
A background worker ingests documents from enterprise sources; a
parent-document retriever with reranking answers questions with citations;
a proposal orchestrator drafts structured proposals from retrieved
evidence.

This is a personal demo project. It captures the pattern — ingestion,
parent-document retrieval, reranking, grounded Q&A, proposal drafting —
without any client code, client data, or proprietary material.

## The problem

Enterprise knowledge lives in scattered documents: policies, capability
statements, past proposals, HR docs, project records. Asking a question
means knowing which document to open. A RAG platform inverts that: ask
the question, get the answer with its sources. And a proposal that used
to take days of hunting through old files starts from a draft built on
what the company has actually done before.

## How it works

```
Sources (files, SharePoint-like, enterprise systems, web)
  -> worker ingests on a schedule: extract, chunk, embed, index
  -> chunks are children of parent documents

Question
  -> retrieve child chunks by term overlap
  -> map children to their parent documents
  -> rerank parents (child scores + title match)
  -> answer from the top parents, with citations
  -> no grounded source -> abstain, never invent

Scope document
  -> proposal orchestrator retrieves relevant past work
  -> drafts a structured outline, each section backed by
     cited evidence from retrieved documents
```

- **Parent-document retrieval.** Small chunks are good for matching, bad
  for answering. Retrieval matches chunks, then returns their parents —
  the full document context the answer actually needs.
- **Reranking.** The first pass is cheap term overlap; the second pass
  re-scores parents by evidence strength and title match, so the best
  document wins, not just the most keyword-dense chunk.
- **Grounded or nothing.** Every claim cites a document. If no document
  clears the threshold, the answer is "I don't have a grounded source" —
  a wrong confident answer costs more than no answer.
- **Proposals from evidence.** A proposal section is only as strong as
  the past work behind it. Each section lists the retrieved documents it
  rests on, so a human can check the draft before it goes out.

## Run it

```bash
python -m src.run_demo
```

Pure standard library, no dependencies. It ingests the synthetic document
set, answers a question with citations, drafts a proposal outline, and
runs the worker sync.

Run the checks:

```bash
python -m unittest discover -s tests -v
```

## What this proves

- **Parents beat chunks.** A question about the safety policy retrieves
  the policy document, not a stray chunk that happens to share a word.
- **Reranking changes the order.** The first pass and the reranked order
  differ — and the test proves the reranked top result is the document
  that actually answers the question.
- **Abstention works.** A question with no grounded source gets an
  abstention, not a hallucinated answer.
- **Ingestion is idempotent.** Re-ingesting the same document creates no
  duplicate chunks; only new or changed documents are indexed.
- **Proposals cite their evidence.** Every section of the draft lists the
  documents it came from.

## Layout

- `src/ingest.py` — connectors, chunking, parent registry, idempotent
  ingestion.
- `src/retrieve.py` — child-chunk index, parent-document retriever,
  reranker.
- `src/qa.py` — the Q&A service: retrieve, rerank, answer or abstain.
- `src/proposals.py` — the proposal orchestrator.
- `src/worker.py` — the scheduler: periodic sync from sources.
- `src/run_demo.py` — the demo walkthrough.
- `data/docs/` — synthetic enterprise documents (fictional company).
- `docs/design.md` — the full design.
- `tests/` — checks for retrieval, reranking, abstention, ingestion,
  and proposals.

## What production adds

A real embedding model and vector store, a language model behind the
answer and the proposal draft, a web app and Teams surface, SSO, a
database for conversations and proposals, and cloud hosting. None of
those are claimed here — the demo is the retrieval and orchestration
mechanism, local only. Generation is extractive templating in this demo;
the model is a plug-in point.
