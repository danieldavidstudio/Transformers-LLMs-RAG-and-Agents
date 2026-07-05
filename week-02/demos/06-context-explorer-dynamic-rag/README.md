<!-- =============================================================================================================== -->
<!-- Universitat Politècnica de Catalunya (UPC)                                                                      -->
<!-- =============================================================================================================== -->

# 📚 Context Explorer — Simple Dynamic RAG

The single-file Context Explorer showed the gap between what the chat UI stores and
what the LLM actually receives. This edition changes **one thing**: the context is no
longer a whole pasted file — it is the **top-K chunks retrieved by meaning from a
collection**, fresh on every turn. The new step sits in the middle, and you watch it:

1. **What the chat UI sends** — the bare turns, nothing else.
2. **Retrieval** — your message becomes the query; the collection returns the nearest
   chunks with their similarity, and you see which ones pass the threshold
   (**→ injected**) and which get dropped (**✗ below threshold**).
3. **What we actually send to the LLM** — system + history + template(message, chunks).
4. **The response — and what persists** — the answer and the token bill; the chunks
   are already gone.

## Setup

```bash
cd context-explorer-dynamic-rag
uv venv && source .venv/bin/activate && uv sync
```

Copy `.env.example` to `.env`. Default is local Ollama — no key, no cost:

```bash
ollama serve
ollama pull qwen3:1.7b
ollama pull nomic-embed-text
```

## Run

```bash
uv run context_explorer_dynamic_rag.py
```

Type `/seed` for a built-in handbook, or ingest real documents first with
[`../../simple-dynamic-rag/ingest.py`](../../simple-dynamic-rag/) and point `PERSIST_PATH`
at the same store.

| Command | What it does |
|---|---|
| `/seed` | load built-in Acme chunks so retrieval lands immediately |
| `/topk N` | how many chunks to retrieve |
| `/threshold X` | similarity gate — watch chunks flip between injected and dropped |
| *(any text)* | one full turn, all four panels |
| *(empty line)* | quit |

## The thing to notice

With the Acme seed loaded, ask something the collection does not cover and read the
similarity column. Surprise: unrelated questions still score around 0.40–0.50 on this
embeddings model, while real answers sit around 0.50–0.70 — the band is narrow.
Play with `/threshold` and watch chunks flip between **→ injected** and **✗ below
threshold**: set it high and off-topic questions inject nothing (the model must say
it doesn't know); set it too high and legitimate questions start starving too. The
gate is a design decision that needs calibrating against your model and your corpus —
and the grounded system prompt is the second line of defense when something slips
through. Now you have felt both.

Built on the course's [`collections-manager`](../../collections-manager/) utility.

## 📖 License

Licensed under [Creative Commons BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) (`CC BY-NC-SA 4.0`).

## 👤 Author

[@granludo](https://github.com/granludo) — Marc Alier, Universitat Politècnica de Catalunya (UPC)
