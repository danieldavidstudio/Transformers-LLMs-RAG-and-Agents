#!/usr/bin/env bash
# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

# Streaming from a raw-HTTP point of view — no SDK.
# With "stream": true the server replies as Server-Sent Events: a stream of
# `data: {...}` lines, one per chunk, each carrying a bit more text in
# choices[0].delta.content, ending with `data: [DONE]`. The SDK parses these
# for you; here you see them arrive on the wire.
#
# curl -N disables buffering, so the lines print the instant they arrive —
# that is the streaming you can watch happen.
[ -f .env ] && { set -a; . ./.env; set +a; }   # load .env if present (bash has no auto-load)
ENDPOINT="${OPENAI_ENDPOINT:-https://api.openai.com/v1}"
MODEL="${MODEL:-gpt-4.1-mini}"

curl -N -s "$ENDPOINT/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"$MODEL"'",
    "messages": [
      {"role": "user", "content": "Say hello in two short sentences."}
    ],
    "stream": true
  }'
echo
