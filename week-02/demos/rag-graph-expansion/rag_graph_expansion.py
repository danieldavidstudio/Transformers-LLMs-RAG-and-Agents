"""Graph expansion + RRF — retrieve by connection, then fuse.

Vector RAG finds chunks that *read like* the question. It fails when the answer
is a chain across documents and the bridge chunk shares no words with the
question. Here: "How fast is the robot built by the company that acquired Acme?"
needs Acme -> Northwind -> Pallet Pup -> 2.1 m/s, but the bridge ("Northwind
builds the Pallet Pup") never mentions "Acme" or "fast", so cosine ranks it low.

The fix is a SECOND retriever run alongside the vector one: pull the entities out
of the question, walk a knowledge graph one or two hops over typed relations, and
collect the chunks you land on. Then fuse the two ranked lists with Reciprocal
Rank Fusion. The graph reaches the bridge by connection; RRF lets it climb into
top-K without displacing what vector search already got right.

Numbers behind this idea: Adrià Guilera Bernabé's TFG (FIB-UPC, 2026) — a graph
layer over LAMB's kb-server, measured on HotPotQA / MuSiQue / 2WikiMultihopQA.

Run:  uv venv && source .venv/bin/activate && uv sync && python rag_graph_expansion.py
"""
import os
import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.environ.get("OPENAI_API_KEY", "ollama"),
)
MODEL = os.environ.get("MODEL", "qwen3:1.7b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")

TOP_K = 4              # chunks we pass to the model — the answer chain here is 3 docs (Acme->Northwind->Pallet Pup) + headroom
RRF_K = 20             # rank-dampening constant (RRF paper uses 60; Adrià uses 20)
GRAPH_WEIGHT = 0.85    # how much the graph list counts vs the vector list

# --- the corpus: built so the BRIDGE chunk (d1) is lexically unlike the question ---
DOCS = {
    "d0": "Acme Robotics was a Barcelona startup founded in 2019. In 2024 it was acquired by Northwind Industries.",
    "d1": "Northwind Industries is a logistics-automation firm. Its flagship product is the Pallet Pup, an autonomous warehouse robot.",  # the bridge
    "d2": "The Pallet Pup has a top speed of 2.1 m/s and an eight-hour battery.",  # the answer
    "d3": "Acme Robotics' early prototypes were shelf-scanning drones, not ground robots.",  # lure: Acme + robot
    "d4": "Warehouse robots typically move between 1 and 3 meters per second depending on payload.",  # lure: robot + speed
    "d5": "Northwind Industries reported strong revenue growth in its 2025 annual report.",  # distractor
}

# Typed relations the graph is built from. In production these are extracted at
# ingestion by an LLM (see README -- classic NER gives only co-occurrence, not
# typed relations); we ship them pre-extracted so the demo is deterministic.
TRIPLES = [
    ("Acme Robotics", "acquired_by", "Northwind Industries"),
    ("Northwind Industries", "builds", "Pallet Pup"),
    ("Pallet Pup", "has_spec", "top speed"),
]
ENTITIES = ["Acme Robotics", "Northwind Industries", "Pallet Pup"]


def embed(texts):
    return [d.embedding for d in client.embeddings.create(model=EMBED_MODEL, input=texts).data]


# index the chunks in Chroma (the vector retriever) ------------------------------
collection = chromadb.Client().create_collection("acme-graph")
ids = list(DOCS)
collection.add(ids=ids, documents=[DOCS[i] for i in ids], embeddings=embed([DOCS[i] for i in ids]))

# which chunks mention which entity (the graph<->text link, built at ingestion) ---
mentions = {e: [cid for cid, t in DOCS.items() if e.lower() in t.lower()] for e in ENTITIES}
# adjacency: entity -> entities it points to
adj = {}
for h, _rel, t in TRIPLES:
    adj.setdefault(h, []).append(t)


def walk(seeds, max_hops=2):
    """BFS over the graph from the question's entities; return entities found, in order."""
    found, frontier = list(seeds), list(seeds)
    for _ in range(max_hops):
        nxt = [t for e in frontier for t in adj.get(e, []) if t not in found]
        found += nxt
        frontier = nxt
    return found


def rrf_merge(rankings, weights, k=RRF_K):
    """Fuse ranked lists: score(id) = sum(weight / (k + rank)). Re-sort by score."""
    scores = {}
    for ranking, w in zip(rankings, weights):
        for rank, cid in enumerate(ranking):
            scores[cid] = scores.get(cid, 0.0) + w / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)


question = "How fast is the robot built by the company that acquired Acme Robotics?"

# 1) vector retriever — the baseline, ranked by similarity
vec_hits = collection.query(query_embeddings=embed([question]), n_results=len(DOCS))
vector_ranking = vec_hits["ids"][0]

# 2) graph retriever — seed with the question's entities, walk, collect chunks
seeds = [e for e in ENTITIES if e.lower() in question.lower()]   # {Acme Robotics}
path = walk(seeds, max_hops=2)                                   # Acme -> Northwind -> Pallet Pup
graph_ranking = []
for ent in reversed(path):              # deepest entity first — the answer end of the chain
    for cid in mentions.get(ent, []):
        if cid not in graph_ranking:
            graph_ranking.append(cid)

# 3) fuse
fused = rrf_merge([vector_ranking, graph_ranking], weights=[1.0, GRAPH_WEIGHT])

print(f"question: {question}\n")
print(f"vector-only top-{TOP_K}: {vector_ranking[:TOP_K]}   (bridge d1? answer d2?)")
print(f"graph hop from {seeds}: {' -> '.join(path)}")
print(f"graph ranking:        {graph_ranking}")
print(f"KG-RAG fused top-{TOP_K}: {fused[:TOP_K]}   (bridge + answer recovered)\n")

context = "\n".join(f"- {DOCS[c]}" for c in fused[:TOP_K])
resp = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": "Answer using only the context. If it is not there, say so."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
    ],
)
print(resp.choices[0].message.content)
