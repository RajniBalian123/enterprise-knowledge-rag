# Design: enterprise document Q&A and proposal drafting

Status: demo of the RAG pattern, with synthetic documents. It does not
claim an embedding model, a vector store, a language model, a web app, or
cloud hosting. Retrieval is term-overlap over an inverted index; generation
is extractive templating. The shape is the same as the production system.

## 1. The flow

```
Sources
  -> worker ingests on a schedule (files, SharePoint-like, enterprise
     systems, public web)
  -> extract text, chunk, index

Question
  -> retrieve child chunks
  -> map to parent documents
  -> rerank parents
  -> answer with citations, or abstain

Scope document
  -> proposal orchestrator retrieves relevant past work
  -> drafts a structured outline with cited evidence per section
```

## 2. Ingestion

Connectors are per-source clients that turn external data into documents:
a file reader, a SharePoint-like source, enterprise-system exports, a web
scraper. Each document gets a stable ID (source + path), so re-ingestion
is idempotent: the same document twice creates no duplicate chunks, and a
changed document replaces its chunks instead of adding to them.

Chunking is paragraph-aware, ~600 characters with 100 overlap. Chunks are
children; the document is the parent. The index maps terms to chunks; the
registry maps chunks to parents.

## 3. Parent-document retrieval

Small chunks match well and answer badly. The retriever therefore works
in two steps:

1. **Match chunks** by term overlap against the query (cheap first pass).
2. **Return parents** — the documents those chunks belong to — deduplicated,
   with each parent's best chunks attached.

The answer is built from parent documents, not from isolated chunks, so
it has the context the question actually needs.

## 4. Reranking

The first pass ranks by keyword overlap, which rewards the most
keyword-dense chunk. The reranker re-scores parents by evidence strength
(the sum of their chunks' scores) plus a title-match bonus, and returns
the top parents in that order. Reranking is what makes the best document
win instead of the loudest chunk.

## 5. Grounded Q&A

The Q&A service retrieves, reranks, and then decides:

- If the top parent clears the relevance threshold, the answer is built
  from its chunks, with a citation (document + section) per claim.
- If the question contains a term that appears in none of the indexed
  documents, or nothing clears the threshold, the answer is an abstention:
  "I don't have a grounded source for that." No invented answer, no
  confident guess. Abstaining on a partly-answerable question is the
  conservative failure mode, and the right one for a grounded system.

In production a language model writes the answer from the retrieved
passages; in this demo the answer is extractive — the most relevant
passages, quoted, with citations. The abstention rule is identical either
way.

## 6. Proposal orchestration

A proposal starts from a scope document. The orchestrator retrieves past
proposals, capability statements, and relevant policies, then drafts a
structured outline — executive summary, approach, relevant experience,
team, timeline — where each section lists the retrieved documents it
rests on. The draft is a starting point for a human, not a finished
proposal: every section can be checked against its sources before it goes
out.

## 7. The worker

A scheduler runs ingestion on a schedule: sync each source, index new or
changed documents, and record what was ingested. The worker is separate
from the API, so a slow source never blocks a question.

## 8. Observability

Every run records: which documents were ingested, which questions were
asked, which parents were retrieved and reranked, and which questions
abstained. That is the data for the questions that matter: which documents
actually answer questions, which questions have no grounded source (a gap
in the knowledge base, not a model failure), and whether the reranker is
earning its keep.

## 9. What production adds

- **Embeddings + vector store** for semantic retrieval (the term-overlap
  index here is a stand-in).
- **A language model** behind the answer and the proposal draft.
- **Web app + Teams surface** with SSO sign-in.
- **Postgres** for conversations, proposals, and templates metadata;
  **blob storage** for templates and uploads.
- **Cloud hosting** with secrets in a vault, telemetry, and a scheduler
  worker as a separate service.
