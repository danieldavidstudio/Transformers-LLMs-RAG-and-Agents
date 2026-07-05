# Give the LLM hands — the agent is a `while` loop

Week 3.1 teaching example. The whole point of this lecture is the reveal:
**there's no magic — an agent is a `while` loop that keeps calling the model
until the model stops asking for tools.**

## What it teaches

1. **The loop IS the agent.** Six lines of `give_the_llm_hands.py` do the
   agentic work — they are marked in the source as lines `1`–`6` inside
   `run_agent()`. Everything else (tool schemas, SQLite, printing, config)
   is plumbing.
   - `1` the `while True` loop
   - `2` call the model, hand it the tool schemas
   - `3` no tool calls returned → that's the final answer, stop
   - `4` append the model's tool-call message to history
   - `5` execute each requested tool
   - `6` append the results, then loop back to `2`
2. **Tools give the model hands.** Without tools an LLM can only talk. With
   `wget` and `execute_sql` it can reach the web and write to a database —
   it *acts*.
3. **Security lives in the scaffolding, not in the prompt.** The `wget` tool
   prints the exact command and refuses to run unless you type `y`. You do
   not ask the model nicely to behave; you gate the dangerous action in code.
   A denial returns a message to the model (it is *told* it was denied) — the
   loop keeps running, nothing crashes.
4. **The model is the bottleneck, not the loop.** Small local models drive
   this loop unevenly — they forget to chain steps, malform tool arguments,
   or stop early. The loop is trivial; the intelligence steering it is the
   model. Point `.env` at a bigger model and the same six lines behave better.

## Prerequisites

Local Ollama running with a small tool-capable model:

```bash
ollama serve
ollama pull qwen3:1.7b
```

## Run

```bash
uv run --with openai python give_the_llm_hands.py
```

Or with your own prompt:

```bash
uv run --with openai python give_the_llm_hands.py "fetch https://api.github.com/users/torvalds and store the login, name and public_repos count"
```

The default prompt fetches a JSON API, asks the model to create a table,
insert the rows, and report how many it stored — a task that needs several
loop iterations, so you watch the `while` loop turn over (`── LLM call #N ──`).

When `wget` is requested you will be prompted: type `y` to allow.

## Config

Defaults are Ollama-first; no `.env` is needed to run locally. Copy
`.env.example` to `.env` to override `OPENAI_BASE_URL`, `OPENAI_API_KEY`,
and `MODEL` (e.g. to point at a frontier or MareNostrum endpoint).
