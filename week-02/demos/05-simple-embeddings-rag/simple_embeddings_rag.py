# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

"""Simple embeddings RAG — the whole dynamic-RAG pipeline, in one readable file.

The single-file demo pasted the WHOLE file into the prompt every turn. Here we do
it properly, and we do it through the course's collections_manager — the same three
calls everything this week is built on. That is the point of an abstraction layer:
this demo, the explorers, the provided simple-dynamic-rag tool and YOUR final
project all speak the same interface, and none of them care what engine sits
underneath.

The pipeline, visible end to end:

  1. CHUNK the knowledge file (a sliding window with overlap — chunking is a for-loop),
  2. INSERT each chunk into a collection (the manager embeds it and indexes it),
  3. on every turn: QUERY the collection with the user's question,
  4. INJECT only the nearest chunks into the prompt, and answer.

Watch prompt_tokens stay small and flat however big knowledge.txt grows — we send
what is RELEVANT, not what is THERE. And notice the question and the chunk that
answers it often share almost no words: retrieval is by meaning.

Two models do two jobs: an EMBEDDINGS model (inside the collection) and a CHAT model
(writes the answers). Empty line to quit. The collection lives in memory for this run.
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

from collections_manager import create_collection, insert, query

load_dotenv()

client = OpenAI(
    base_url=os.environ.get("OPENAI_ENDPOINT", "http://localhost:11434/v1"),
    api_key=os.environ.get("OPENAI_API_KEY", "ollama"),
)
MODEL = os.environ.get("MODEL", "qwen3:1.7b")

# The knobs of a RAG pipeline. Change them and feel the trade-offs:
#   CHUNK_SIZE  — bigger keeps facts together but pulls in noise; smaller is precise
#                 but can cut a single fact in two.
#   CHUNK_OVERLAP — a shared margin so a fact split at a boundary survives whole.
#   TOP_K       — how many nearest chunks to retrieve and inject per question.
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "320"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "40"))
TOP_K = int(os.environ.get("TOP_K", "3"))


def chunk(text, size, overlap):
    """Slide a window of `size` characters across the text, stepping by size-overlap."""
    step = max(1, size - overlap)
    pieces = []
    i = 0
    while i < len(text):
        piece = text[i:i + size].strip()
        if piece:
            pieces.append(piece)
        i += step
    return pieces


# --- Build the collection once, at startup ------------------------------------
# create_collection with no persist_path -> in memory, rebuilt every run.
# The manager's default embedding function reads EMBED_MODEL / OPENAI_ENDPOINT
# from .env (out of the box: local Ollama + nomic-embed-text).
text = open(os.path.join(os.path.dirname(__file__), "knowledge.txt")).read()
col = create_collection("knowledge", description="simple-embeddings-rag demo", metric="cosine")
for piece in chunk(text, CHUNK_SIZE, CHUNK_OVERLAP):
    result = insert(col, piece, {"source": "knowledge.txt"})   # chunk_number auto-assigned
    if not result["ok"]:
        print(f"  ✘ {result['error']}")

print(f"Simple embeddings RAG · chat={MODEL} · {col.count()} chunks "
      f"(size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}) · top-{TOP_K} per question")
print("Ask about the document. Empty line to quit.\n")

SYSTEM = "Answer using only the context. If it is not there, say so."
history = []  # BARE turns only — retrieved chunks are rebuilt each turn, never stored

while True:
    question = input("you> ").strip()
    if not question:
        break

    # Retrieve by MEANING: the manager embeds the question and returns the nearest chunks.
    hits = query(col, question, top_k=TOP_K)

    # Inject ONLY the retrieved chunks — not the whole file.
    context = "\n----\n".join(h["chunk"] for h in hits)
    augmented = f"Context:\n----\n{context}\n----\n\nQuestion: {question}"
    messages = [{"role": "system", "content": SYSTEM}] + history + [{"role": "user", "content": augmented}]

    resp = client.chat.completions.create(model=MODEL, messages=messages)
    answer = resp.choices[0].message.content
    print(f"bot> {answer}")

    # Show what retrieval did: which chunks, how similar, and how few tokens we sent.
    retrieved = ", ".join(f"{h['metadata']['source']}::{h['metadata']['chunk_number']}"
                          f"(sim {h['similarity']:.2f})" for h in hits)
    print(f"     [retrieved {retrieved}]")
    print(f"     [{resp.usage.prompt_tokens} prompt tokens — only {TOP_K} chunks rode along, "
          f"not the whole file]\n")

    history += [{"role": "user", "content": question},
                {"role": "assistant", "content": answer}]
