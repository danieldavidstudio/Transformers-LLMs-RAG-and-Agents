# single-file RAG — cheating at solitaire

The simplest thing that could possibly be called RAG: read the whole knowledge
file, paste it into the prompt, and chat with it. No chunking, no embeddings, no
vector store. The model answers because the answer is sitting in its context
window. It is a tiny chat loop — about thirty lines you can read end to end.

This works, and for a small enough corpus you should just do this. The lesson is
where it breaks: the **entire file is re-sent on every turn**, so `prompt_tokens`
scales with the size of your knowledge base, not the size of the question. Ask a
few questions and watch the `prompt_tokens` line climb while your questions stay
short. Then ask an off-corpus one (e.g. "Who is the CEO of Tesla?") and watch the
grounded answer fail honestly — proof the model is reading the context, not its
training data.

## Setup

```bash
cd single-file-rag
uv venv && source .venv/bin/activate && uv sync
```

Copy `.env.example` to `.env`. The defaults assume a local Ollama (no API key, no
money, no internet):

```bash
OPENAI_API_KEY=ollama
MODEL=qwen3:1.7b
OPENAI_ENDPOINT=http://localhost:11434/v1
```

Point `OPENAI_ENDPOINT` at any OpenAI-compatible API to use a different provider
(and spell `MODEL` the way that provider spells it).

## Run

```bash
uv run single_file_rag.py
```

Chat with the document; each turn prints the answer and the `prompt_tokens` count.
The whole file lands in `prompt_tokens` — on every turn — so the number climbs as
you go, even when your questions are tiny. That is the cost this approach pays, and
the reason the next rung (embeddings + retrieval) exists. Empty line to quit.
