# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

"""Single-file RAG — cheating at solitaire, as a chat.

No chunking, no index, no retrieval. Read the whole knowledge file, paste it into
the prompt every turn, and chat with it. The model "knows" because the answer is in
its context. The catch — and the whole lesson — is that you re-send the ENTIRE file
on every single turn: watch prompt_tokens climb while your questions stay short.

Empty line to quit. No persistence — the conversation lives in memory for this run.
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.environ.get("OPENAI_ENDPOINT", "http://localhost:11434/v1"),
    api_key=os.environ.get("OPENAI_API_KEY", "ollama"),
)
MODEL = os.environ.get("MODEL", "qwen3:1.7b")

# The whole file becomes the context. No selection — everything goes in, every turn.
context = open(os.path.join(os.path.dirname(__file__), "knowledge.txt")).read()
SYSTEM = "Answer using only the context. If it is not there, say so."

history = []  # the conversation so far — BARE turns only (what a real chat UI keeps)
print(f"Single-file RAG chat · model={MODEL} · knowledge.txt ({len(context)} chars)")
print("Ask about the document. Empty line to quit.\n")

while True:
    question = input("you> ").strip()
    if not question:
        break

    # Naive RAG: paste the WHOLE file beside the question — rebuilt every turn.
    augmented = f"Context:\n----\n{context}\n----\n\nQuestion: {question}"
    messages = [{"role": "system", "content": SYSTEM}] + history + [{"role": "user", "content": augmented}]

    resp = client.chat.completions.create(model=MODEL, messages=messages)
    answer = resp.choices[0].message.content
    print(f"bot> {answer}")
    print(f"     [{resp.usage.prompt_tokens} prompt tokens — the whole file rode along again]\n")

    # Remember only the BARE turns, not the augmented message — so the file is NOT
    # accumulated in history; it is re-injected fresh on the next turn instead.
    history += [{"role": "user", "content": question},
                {"role": "assistant", "content": answer}]
