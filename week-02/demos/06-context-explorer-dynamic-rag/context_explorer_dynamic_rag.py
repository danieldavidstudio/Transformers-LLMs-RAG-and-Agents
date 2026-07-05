# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

# =============================================================================================================== #
# Universitat Politècnica de Catalunya (UPC)                                                                      #
# =============================================================================================================== #

"""
📚 Context Explorer — SIMPLE DYNAMIC RAG: watch retrieval choose the context.

The single-file explorer showed the gap between what the chat UI stores and what
the LLM receives. This one changes ONE thing: the context is no longer a whole
pasted file — it is the top-K chunks retrieved BY MEANING from a collection, fresh
on every turn. Watch the new step in the middle:

    🖥️  CHAT UI        sends:  history (bare) + your latest message
                                  |
                                  v
    🛠️  ASSISTANT ENDPOINT  (STATELESS)
            1. your message becomes the QUERY
            2. the collection returns the nearest chunks (top-K, over a threshold)
            3. builds: [system] + [history] + [ template(your message, THOSE chunks) ]
                                  |
                                  v
    🧠  LLM            returns:  the response only
                                  ^
    🖥️  CHAT UI        appends (your message, response) to history   ✗ chunks NOT saved

Ingest documents first with simple-dynamic-rag/ingest.py (point PERSIST_PATH at the
same store), or type /seed for a built-in handbook.

In-chat commands:
    /seed        load the built-in Acme chunks so retrieval lands immediately
    /topk N      change how many chunks are retrieved
    /threshold X change the similarity threshold (chunks below it are dropped)
    (empty line) quit
"""
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich import box

from collections_manager import create_collection, insert, query

load_dotenv()

# High-contrast Rich theme — matches the context-explorer house style.
BG = "grey23"
ON_BG = f"on {BG}"
TEXT = f"bright_white {ON_BG}"
TEXT_DIM = f"grey84 {ON_BG}"
ACCENT = f"bold cyan1 {ON_BG}"
NUM = f"bright_yellow {ON_BG}"
GOOD = f"bright_green {ON_BG}"
BAD = f"orange1 {ON_BG}"

console = Console()

client = OpenAI(
    base_url=os.environ.get("OPENAI_ENDPOINT", "http://localhost:11434/v1"),
    api_key=os.environ.get("OPENAI_API_KEY", "ollama"),
)
MODEL = os.environ.get("MODEL", "qwen3:1.7b")

SYSTEM = "Answer using only the context. If it is not there, say you don't know."
TEMPLATE = "Context:\n----\n{context}\n----\n\nQuestion: {user_input}"

SEED = [
    ("acme-handbook", "The warehouse robot's top speed is 2.4 metres per second."),
    ("acme-handbook", "The Pallet Pup carries up to 600 kg and its battery lasts nine hours."),
    ("acme-handbook", "Acme Robotics was founded in 2019 in Girona, Catalonia."),
    ("acme-handbook", "Every Pallet Pup ships with an emergency stop any nearby worker can press."),
    ("acme-handbook", "A Pallet Pup costs 18,900 euros; fleets of ten or more get a volume discount."),
    ("recipes", "The recipe needs two eggs and a cup of flour."),
]


def _truncate(text: str, width: int = 70) -> str:
    one = " ".join(text.split())
    return one if len(one) <= width else one[: width - 1] + "…"


def show_ui_send(history: list, user_input: str) -> None:
    body = Text()
    body.append("The chat UI sends the BARE conversation — no system prompt, no chunks:\n\n", style=TEXT_DIM)
    for m in history:
        body.append(f"  {m['role']:9s} ", style=ACCENT)
        body.append(_truncate(m["content"]) + "\n", style=TEXT_DIM)
    body.append(f"  user      ", style=ACCENT)
    body.append(user_input + "\n", style=TEXT)
    console.print(Panel(body, title="🖥️ 1 · what the CHAT UI sends", border_style="bright_cyan",
                        style=ON_BG, padding=(0, 1)))


def show_retrieval(user_input: str, kept: list, dropped: list, top_k: int, threshold: float) -> None:
    table = Table(box=box.SIMPLE_HEAVY, style=ON_BG, header_style=ACCENT,
                  title=f"query = the user message · top-{top_k} · threshold {threshold}",
                  title_style=TEXT_DIM)
    table.add_column("similarity", justify="right", style=NUM)
    table.add_column("source", style=TEXT_DIM)
    table.add_column("#", justify="right", style=TEXT_DIM)
    table.add_column("chunk", style=TEXT)
    table.add_column("", style=GOOD)
    for h in kept:
        m = h["metadata"]
        table.add_row(f"{h['similarity']:.3f}", str(m.get("source")), str(m.get("chunk_number")),
                      _truncate(h["chunk"], 56), "→ injected")
    for h in dropped:
        m = h["metadata"]
        table.add_row(Text(f"{h['similarity']:.3f}", style=BAD), str(m.get("source")),
                      str(m.get("chunk_number")), Text(_truncate(h["chunk"], 56), style=TEXT_DIM),
                      Text("✗ below threshold", style=BAD))
    console.print(Panel(table, title="🔎 2 · RETRIEVAL — the collection chooses the context",
                        border_style="bright_magenta", style=ON_BG, padding=(0, 1)))


def show_api_request(messages: list) -> None:
    payload = json.dumps({"model": MODEL, "messages": messages}, indent=2, ensure_ascii=False)
    if len(payload) > 2400:
        payload = payload[:2400] + "\n  ... (truncated for display)"
    console.print(Panel(Syntax(payload, "json", background_color="grey11", word_wrap=True),
                        title="🧠 3 · what we actually send to the LLM",
                        border_style="bright_yellow", style=ON_BG, padding=(0, 1)))


def show_response(answer: str, usage, kept: int, total: int) -> None:
    body = Text()
    body.append(answer + "\n\n", style=TEXT)
    body.append(f"prompt_tokens={usage.prompt_tokens} · completion_tokens={usage.completion_tokens} "
                f"· {kept} chunks rode along, out of {total} in the collection\n", style=NUM)
    body.append("History keeps only (your message, this answer). The chunks are already gone.", style=TEXT_DIM)
    console.print(Panel(body, title="💬 4 · the response — and what persists",
                        border_style="bright_green", style=ON_BG, padding=(0, 1)))


def main() -> None:
    persist = os.environ.get("PERSIST_PATH", "./collections-store")
    col = create_collection(os.environ.get("COLLECTION", "handbook"),
                            metric="cosine", persist_path=persist)
    top_k = int(os.environ.get("TOP_K", "4"))
    threshold = float(os.environ.get("THRESHOLD", "0.4"))

    intro = Text()
    intro.append("Same three layers as the single-file explorer — but the context is now ", style=TEXT)
    intro.append("retrieved by meaning", style=ACCENT)
    intro.append(f" from a collection ({col.count()} chunks, {persist}).\n", style=TEXT)
    intro.append("Ask something; watch which chunks get chosen — and which get dropped.\n\n", style=TEXT)
    intro.append("/seed   /topk N   /threshold X   (empty line = quit)", style=TEXT_DIM)
    console.print(Panel(intro, title="📚 Context Explorer — simple dynamic RAG",
                        border_style="bright_magenta", style=ON_BG, padding=(1, 2)))

    history = []
    while True:
        try:
            line = console.input("[bold bright_cyan]📝 you: [/bold bright_cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            break
        if line == "/seed":
            for source, chunk in SEED:
                r = insert(col, chunk, {"source": source, "title": source,
                                        "doc_url": "seed", "md_url": "seed",
                                        "chunking_strategy": "seed", "ingested_at": "seed"})
                mark = "✔" if r["ok"] else "✘"
                console.print(Text(f"  {mark} {r['id']}{'' if r['ok'] else ' — ' + r['error']}", style=GOOD if r["ok"] else BAD))
            continue
        if line.startswith("/topk"):
            top_k = int(line.split()[1]); console.print(Text(f"  top_k = {top_k}", style=NUM)); continue
        if line.startswith("/threshold"):
            threshold = float(line.split()[1]); console.print(Text(f"  threshold = {threshold}", style=NUM)); continue

        show_ui_send(history, line)

        # Retrieve WITHOUT the threshold first, so the dropped chunks are visible too.
        all_hits = query(col, line, top_k=top_k)
        kept = [h for h in all_hits if h["similarity"] >= threshold]
        dropped = [h for h in all_hits if h["similarity"] < threshold]
        show_retrieval(line, kept, dropped, top_k, threshold)
        if not kept:
            console.print(Text("  nothing passes the threshold — nothing to inject. "
                               "Ingest documents, /seed, or lower /threshold.\n", style=BAD))
            continue

        context = "\n\n".join(f"[{h['metadata'].get('title')} · chunk {h['metadata'].get('chunk_number')} "
                              f"· similarity {h['similarity']:.3f}]\n{h['chunk']}" for h in kept)
        augmented = TEMPLATE.format(context=context, user_input=line)
        messages = [{"role": "system", "content": SYSTEM}] + history + [{"role": "user", "content": augmented}]
        show_api_request(messages)

        resp = client.chat.completions.create(model=MODEL, messages=messages)
        answer = resp.choices[0].message.content
        show_response(answer, resp.usage, len(kept), col.count())

        history += [{"role": "user", "content": line},
                    {"role": "assistant", "content": answer}]

    console.print(Text("bye.", style=TEXT_DIM))


if __name__ == "__main__":
    main()
