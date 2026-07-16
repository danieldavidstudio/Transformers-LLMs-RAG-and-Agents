# Graph expansion + RRF — retrieve by connection, then fuse

The fourth rung of Week 2. `rag-context-aware` fixed the *query*; this fixes a
problem a perfect query can't touch: the **multi-hop** question, where the answer
is a chain across documents and the bridge chunk shares no words with the question.

Worked example: *"How fast is the robot built by the company that acquired Acme
Robotics?"* The answer needs three links — Acme → Northwind → Pallet Pup → 2.1 m/s
— and the bridge sentence (*"Northwind builds the Pallet Pup"*) mentions neither
"Acme" nor "fast". Cosine ranks it low, so vector RAG never sees it.

The pipeline, in ~90 honest lines:

1. **Vector retriever** (Chroma) — the baseline, ranked by similarity. It misses
   the bridge.
2. **Graph retriever** — pull the entities out of the question, **walk the graph**
   one or two hops over typed relations (`acquired_by`, `builds`, `has_spec`), and
   collect the chunks you land on. This reaches the bridge by *connection*.
3. **Reciprocal Rank Fusion** — `score(id) = Σ weight / (k + rank)` across both
   lists, re-sorted. Five lines. `RRF_K=20` and `GRAPH_WEIGHT=0.85` are the values
   Adrià picked from a 98-config sweep. The fused top-K recovers the bridge **without**
   displacing what vector search already got right.

### Why the relations come from an LLM (not classic NER)

This demo ships the graph **pre-extracted** (`TRIPLES`) so it's deterministic. In
production the relations are extracted at ingestion by an **LLM** with structured
output, because classic NER (spaCy, TF-IDF) gives you *entities* and at best
*co-occurrence* — "these two words appeared near each other" — which is semantically
empty and impossible for a human to curate. **Named-entity recognition is not
relation extraction.** The extraction cost lands once, at ingest, not per query.

### Knobs

- `TOP_K` — chunks passed to the model.
- `RRF_K` — rank dampening (RRF paper uses 60; lower = top ranks dominate more).
- `GRAPH_WEIGHT` — how much the graph list counts. Turn it to `0.0` and the bridge
  falls back out of top-K — that's the demo for "fusion is doing the work."

### Run it

```bash
cd week-02/demos/rag-graph-expansion
uv venv && source .venv/bin/activate && uv sync
python rag_graph_expansion.py
```

Needs a local Ollama serving a chat model and `nomic-embed-text`
(`ollama pull nomic-embed-text`). No API key, no money. See `.env.example`.

### The lesson

The graph **never degrades** the baseline and adds recall **in proportion to how
multi-hop your corpus is** — big on entity-chain corpora, near-zero on generalist
ones. The cost is one extra LLM call per query (entity extraction), not the graph
traversal itself. The measured numbers behind all of this come from **Adrià Guilera
Bernabé's TFG** (FIB-UPC, 2026), which built and benchmarked a graph layer over the
LAMB `kb-server` on three public multi-hop QA datasets. Diagnose your corpus before
reaching for it.
