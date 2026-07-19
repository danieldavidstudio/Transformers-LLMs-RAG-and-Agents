# Lecture 3 — calling the LLM

It is all **JSON over HTTP**. The same **Chat Completions** call — `messages`
in, `choices[0].message.content` out — reaches OpenAI, OpenRouter, Groq, Mistral
and your laptop's local model alike. One wire format, every provider. Here it is
two ways (raw `curl` and the Python SDK), plus two variations on the same call:
streaming and images.

```
chat-completions/   the call itself      (/v1/chat/completions)
  curl.sh             raw HTTP, no SDK
  call.py             the same call via the openai SDK
streaming/          tokens as they are produced (the typewriter effect)
  curl.sh             raw SSE (data: chunks) over the wire — no SDK
  stream.py           stream=True over chat completions
multimodal/         send an image, not just text
  send_image.py       content as a list of parts (text + image)
```

## Run it

Each folder is self-contained and reads its own `.env`. Copy the example,
fill it in, and run **from inside the folder** so the right `.env` is picked up:

```bash
cd chat-completions
cp ../.env.example .env        # set OPENAI_ENDPOINT / OPENAI_API_KEY / MODEL
```

Raw HTTP — nothing but `curl` (the script sources `.env` for you):

```bash
bash curl.sh
```

Python — via `uv`, no manual install:

```bash
uv run --with openai --with python-dotenv python call.py
```

The same two commands work in `streaming/` and `multimodal/`. One caveat:
**vision** (`multimodal/`) needs a vision-capable model, so point its `.env` at a
provider that has one. Plain chat completions (`chat-completions/`, `streaming/`)
run against anything that speaks the wire format, including a local model.

## Same wire, different substrate

The Chat Completions shape is not OpenAI-only. Point the same Python code at a
different `base_url` and it calls a different machine:

```python
from openai import OpenAI

# your laptop, via Ollama — no key, no money, no internet
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
```

Same client, same call, same JSON. The substrate is replaceable; the interface
is portable. That portability is the whole point — so we build on the format
everyone speaks, not on any one vendor's proprietary endpoint.


---

© 2026 **Marc Alier i Forment** (Universitat Politècnica de Catalunya) · <https://wasabi.essi.upc.edu/ludo> · <https://lamb-project.org>
BSC Agents Course — *Transformers, LLMs, RAG and Agents: From Theory to Production*.
Licensed under [Creative Commons BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/): reuse must credit the author, no commercial use, derivatives under the same license.
