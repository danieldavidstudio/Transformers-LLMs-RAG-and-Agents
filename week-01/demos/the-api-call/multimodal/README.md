# Sending an image to the API

A multimodal model reads images as well as text — but the call is the **same
chat-completions request** you already know. The only difference is the shape of
a message's `content`: instead of a plain string it becomes a **list of parts**,
and one part is an image. The image is given either as a **URL** the server
fetches, or inlined as a **base64 `data:` URI** (useful for local or private
files). Endpoint, SDK, and the `usage` record are unchanged.

You need a **vision-capable model** (e.g. `gpt-4.1-mini`, `gpt-4o`). A tiny local
model usually cannot see images.

## Run it

```bash
cp ../.env.example .env        # set a vision MODEL + your key
uv run --with openai --with python-dotenv python send_image.py                  # the bundled image
uv run --with openai --with python-dotenv python send_image.py path/to/photo.jpg
uv run --with openai --with python-dotenv python send_image.py https://example.com/photo.jpg
```

With no argument it sends the bundled **`great-atuin.png`** — the Great A'Tuin
carrying the elephants and the Disc (turtles all the way down) — and asks the
model what is holding up the world. A good first test that vision is working,
and a fitting one for this course. It prints the model's answer plus the token
`usage`.

---

© 2026 **Marc Alier i Forment** (Universitat Politècnica de Catalunya) · <https://wasabi.essi.upc.edu/ludo> · <https://lamb-project.org>
BSC Agents Course — *Transformers, LLMs, RAG and Agents: From Theory to Production*.
Licensed under [Creative Commons BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/): reuse must credit the author, no commercial use, derivatives under the same license.
