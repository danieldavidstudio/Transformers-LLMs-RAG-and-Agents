<!-- =============================================================================================================== -->
<!-- Universitat Politècnica de Catalunya (UPC)                                                                      -->
<!-- =============================================================================================================== -->

# 🐢 Turtle — a custom agent shipped as a CLI

The defining move of the methodology, made concrete. You take a small hand-built agent
loop, **harvest** what a prototype taught you, **fold** it into your own loop plus a
session store and an explicit security check, and **ship** it as a command-line tool — not
a chat box in the corner of a web page.

```
turtle "list the files here and tell me which is largest"   # -> answer + a session id
turtle <session-id> "now show me its first lines"           # continue that session
turtle --list-sessions
turtle --replay <session-id>
turtle --help                                               # works, for a human AND an agent
```

**Why a CLI?** Because the next agent has to be able to drive it. *"A chat-window-in-a-corner
is not testable by another agent; a CLI is."* See `../agent-tests-agent/`.

The loop is the invariant ~30 lines. The two additions over a bare loop are the **session
store** (continue a conversation) and the **security check** that runs *before every tool
call* — a critical constraint lives in host code, deterministic, never in the prompt. Ask
the Turtle to `rm` a file and watch the gate deny it.

## Setup & run

```bash
uv venv && source .venv/bin/activate && uv sync     # or: pip install openai
cp .env.example .env                                # then edit
uv run turtle.py "what is the largest file here?"
```

Ollama-first (no key, no money): `OPENAI_BASE_URL=http://localhost:11434/v1`, `MODEL=qwen3:1.7b`
(use a tool-calling model; e.g. `qwen3.6:27b` on a bigger box).

## 📖 License & author

Licensed under **CC BY-NC-SA 4.0**. © 2026 **Marc Alier i Forment** (UPC) ·
<https://wasabi.essi.upc.edu/ludo> · <https://lamb-project.org>. BSC Agents Course —
*Transformers, LLMs, RAG and Agents: From Theory to Production*.
