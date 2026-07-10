# EASY-ASSISTANT - Week 2 Dynamic RAG

This exercise is a small FastAPI + vanilla JavaScript assistant app. Assistants
keep their existing prompts and upload workflow, but uploaded documents are now
ingested into a persistent vector collection and retrieved dynamically at chat
time.

## Structure

- `backend/` - FastAPI application
- `frontend/` - vanilla HTML, CSS, and JavaScript
- `data/assistants.json` - assistant metadata
- `data/assistants/<assistant_id>/knowledge.txt` - compatibility copy of the uploaded document
- `data/assistants/<assistant_id>/collections-store/collection.json` - persistent chunk embeddings
- `docker-compose.yml` - local service orchestration

## Ollama Models

The default `.env.example` assumes Ollama's OpenAI-compatible API:

```sh
ollama pull qwen3:1.7b
ollama pull nomic-embed-text
```

`qwen3:1.7b` is used for chat by default. `nomic-embed-text` is used for
document and question embeddings.

## Run

Copy `.env.example` to `.env`, then start the app:

```sh
docker compose up --build
```

Open the app at:

```text
http://localhost:6661
```

If the backend runs in Docker and Ollama runs on your host machine, you may need
to set these endpoints in `.env`:

```env
OPENAI_ENDPOINT=http://host.docker.internal:11434/v1
EMBEDDING_ENDPOINT=http://host.docker.internal:11434/v1
```

For local Python without Docker, install dependencies and run Uvicorn:

```sh
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

## Configuration

Chat model settings:

```env
OPENAI_ENDPOINT=http://localhost:11434/v1
OPENAI_API_KEY=ollama
MODEL=qwen3:1.7b
```

Embedding settings:

```env
EMBEDDING_ENDPOINT=http://localhost:11434/v1
EMBEDDING_API_KEY=ollama
EMBEDDING_MODEL=nomic-embed-text
```

Dynamic RAG settings:

```env
TOP_K=4
RAG_THRESHOLD=0.50
```

`TOP_K` controls the maximum number of chunks added to `{context}`. 
`RAG_THRESHOLD` is the minimum cosine similarity a chunk must have before it can
be used. Raising the threshold gives stricter retrieval; lowering it includes
more loosely related chunks.

## Upload And Ingestion

1. Create an assistant with a system prompt and a prompt template containing
   `{context}` and `{user_input}`.
2. Upload a UTF-8 `.txt` or `.md` document.
3. The backend saves a compatibility copy at
   `data/assistants/<assistant_id>/knowledge.txt`.
4. The backend chunks the document with a simple character sliding window:
   `800` characters per chunk with `100` characters of overlap.
5. Each chunk is embedded with the configured embedding model.
6. The chunk text, metadata, and embedding vectors are persisted in
   `data/assistants/<assistant_id>/collections-store/collection.json`.

Replacing a document replaces that assistant's collection.

## Chat Retrieval

When you chat with an assistant:

1. The user question is embedded.
2. The assistant's persisted chunk vectors are loaded.
3. Chunks are ranked by cosine similarity.
4. The app keeps the top `TOP_K` chunks above `RAG_THRESHOLD`.
5. `{context}` is built only from retrieved chunks, not the whole document.
6. The response still includes `filled_prompt`, `messages`, `usage`, and
   `finish_reason`.

The response also includes `retrieved_chunks` with each chunk's id, similarity,
text, preview, and metadata. The frontend debug tab shows those retrieved chunks
after assistant chat requests.

Streaming chat and vision chat remain available and unchanged.
