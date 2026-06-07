# Lecture 3 — calling the LLM

Four ways to make the same call. Two transports (raw `curl` and the Python
SDK), against two OpenAI endpoints (the classic **Chat Completions** API and
the newer **Responses** API). The point of the lecture: it is all JSON over
HTTP, and one wire format covers every provider.

```
chat-completions/   the classic endpoint  (/v1/chat/completions)
  curl.sh             raw HTTP, no SDK
  call.py             the same call via the openai SDK
responses/          the newer endpoint    (/v1/responses)
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

The same two commands work in `responses/`, `streaming/`, and `multimodal/`.
Two caveats on where each can point: the **Responses API** (`responses/`) and
**vision** (`multimodal/`) are OpenAI-specific — point their `.env` at OpenAI.
Plain chat completions (`chat-completions/`, `streaming/`) run against anything
that speaks the wire format, including a local model.

## Chat Completions vs Responses

| | Chat Completions | Responses |
|---|---|---|
| endpoint | `/v1/chat/completions` | `/v1/responses` |
| input | `messages: [...]` | `input` (+ `instructions`) |
| output | `choices[0].message.content` | `output_text` |
| status | the de-facto standard everyone speaks | OpenAI's newer, simpler surface |

Chat Completions is the format every other provider copied, so it is what you
target for portability. Responses is OpenAI's own newer endpoint — cleaner, but
not (yet) universal.

## Same wire, different substrate

The Chat Completions shape is not OpenAI-only. Point the same Python code at a
different `base_url` and it calls a different machine:

```python
from openai import OpenAI

# your laptop, via Ollama — no key, no money, no internet
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
```

Same client, same call, same JSON. The substrate is replaceable; the interface
is portable.


---

© 2026 **Marc Alier i Forment** (Universitat Politècnica de Catalunya) · <https://wasabi.essi.upc.edu/ludo> · <https://lamb-project.org>
BSC Agents Course — *Transformers, LLMs, RAG and Agents: From Theory to Production*.
Licensed under [Creative Commons BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/): reuse must credit the author, no commercial use, derivatives under the same license.
