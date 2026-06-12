<!-- =============================================================================================================== -->
<!-- Universitat Politècnica de Catalunya (UPC)                                                                      -->
<!-- =============================================================================================================== -->

# 🧾 CLI vs MCP — count the tokens

You built an MCP server and it worked. Now the question you could not ask before: *was it
the cheapest way to give the model that capability?* This demo makes the bill visible for
one GitHub task, two ways — and the number is the point, not the plumbing.

- **CLI path** — the model already knows `gh` from its training. No schema loaded. It emits
  one command; you run it; the result comes back. Catalogue overhead: **zero**.
- **MCP path** — the GitHub MCP server injects its tool **catalogue** (dozens of JSON
  schemas) at the head of every session, before any work happens.

It tokenises a real `gh` interaction (run live if you have `gh`; otherwise a captured
sample) and sets it against the catalogue. Published receipts cited in the chapter:
~35× more tokens via MCP on matched tasks [MindStudio 2026]; ~1,365 vs ~44,026 tokens for
one task [Vensas 2026]; ~55,000 vs ~200 tokens at session start [Reinhard 2026].

```bash
uv venv && source .venv/bin/activate && uv pip install tiktoken
uv run gh_token_diff.py
```

Needs `tiktoken` (real token counting) and, optionally, `gh` on PATH for a live call.

## 📖 License & author

Licensed under **CC BY-NC-SA 4.0**. © 2026 **Marc Alier i Forment** (UPC) ·
<https://wasabi.essi.upc.edu/ludo> · <https://lamb-project.org>. BSC Agents Course.
