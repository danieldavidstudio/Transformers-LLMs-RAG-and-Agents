# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

"""Single-file RAG — cheating at solitaire.

No chunking, no index, no retrieval. Read the whole knowledge file, paste it
into the prompt, ask. The model "knows" because the answer is in its context.
The catch: you re-send the entire file on every single turn — watch prompt_tokens.
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

# The whole file becomes the context. No selection — everything goes in.
context = open(os.path.join(os.path.dirname(__file__), "knowledge.txt")).read()
user_input = "What does Acme Robotics make, and where is it headquartered?"

prompt = f"Context:\n----\n{context}\n----\n\nQuestion: {user_input}"

resp = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": "Answer using only the context. If it is not there, say so."},
        {"role": "user", "content": prompt},
    ],
)

print(resp.choices[0].message.content)
print(resp.usage)  # the whole file is in prompt_tokens — every turn
