import base64
import json
import math
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="Easy ChatGPT API")
project_dir = Path(__file__).resolve().parents[2]
frontend_dir = project_dir / "frontend"
assistants_file = project_dir / "data" / "assistants.json"
load_dotenv(project_dir / ".env")

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100
SUPPORTED_DOCUMENT_EXTENSIONS = {".txt", ".md"}


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    messages: list[dict[str, str]]
    usage: dict[str, Any]
    finish_reason: str | None


class AssistantChatRequest(BaseModel):
    assistant_id: str
    message: str


class AssistantChatResponse(BaseModel):
    reply: str
    assistant_id: str
    assistant_name: str
    filled_prompt: str
    messages: list[dict[str, str]]
    retrieved_chunks: list[dict[str, Any]] = Field(default_factory=list)
    usage: dict[str, Any]
    finish_reason: str | None


class VisionResponse(BaseModel):
    prompt: str
    reply: str
    messages: list[dict[str, Any]]
    usage: dict[str, Any]
    finish_reason: str | None


class AssistantCreate(BaseModel):
    name: str
    system_prompt: str
    prompt_template: str

    @field_validator("name", "system_prompt")
    @classmethod
    def text_must_not_be_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value

    @field_validator("prompt_template")
    @classmethod
    def template_must_have_placeholders(cls, value: str) -> str:
        value = value.strip()
        missing = [
            placeholder
            for placeholder in ("{context}", "{user_input}")
            if placeholder not in value
        ]
        if missing:
            raise ValueError(
                f"Prompt template must include: {', '.join(missing)}."
            )
        return value


class Assistant(AssistantCreate):
    id: str
    created_at: str
    has_document: bool = False
    document_filename: str | None = None
    document_char_count: int | None = None
    document_chunk_count: int | None = None


def read_assistants() -> list[Assistant]:
    assistants_file.parent.mkdir(parents=True, exist_ok=True)

    if not assistants_file.exists():
        assistants_file.write_text("[]\n", encoding="utf-8")

    try:
        data = json.loads(assistants_file.read_text(encoding="utf-8"))
        return [Assistant.model_validate(item) for item in data]
    except (json.JSONDecodeError, OSError, ValueError) as error:
        raise HTTPException(
            status_code=500,
            detail="Could not read the assistants file.",
        ) from error


def write_assistants(assistants: list[Assistant]) -> None:
    try:
        assistants_file.write_text(
            json.dumps(
                [assistant.model_dump() for assistant in assistants],
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="Could not save the assistant.",
        ) from error


def get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError as error:
        raise HTTPException(
            status_code=500,
            detail=f"{name} must be an integer.",
        ) from error


def get_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return float(value)
    except ValueError as error:
        raise HTTPException(
            status_code=500,
            detail=f"{name} must be a number.",
        ) from error


def assistant_dir(assistant_id: str) -> Path:
    return assistants_file.parent / "assistants" / assistant_id


def collection_dir(assistant_id: str) -> Path:
    return assistant_dir(assistant_id) / "collections-store"


def collection_file(assistant_id: str) -> Path:
    return collection_dir(assistant_id) / "collection.json"


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be greater than or equal to 0 and smaller than chunk_size.")

    chunks = []
    start = 0
    chunk_index = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(
                {
                    "id": f"chunk-{chunk_index:04d}",
                    "text": chunk,
                    "start": start,
                    "end": end,
                }
            )
            chunk_index += 1

        if end == len(text):
            break
        start = max(end - overlap, start + 1)

    return chunks


def embedding_client() -> tuple[OpenAI, str]:
    endpoint = os.getenv("EMBEDDING_ENDPOINT", "http://localhost:11434/v1")
    api_key = os.getenv("EMBEDDING_API_KEY", "ollama")
    model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    return OpenAI(base_url=endpoint, api_key=api_key), model


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    client, model = embedding_client()
    try:
        response = client.embeddings.create(model=model, input=texts)
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not create embeddings. Check EMBEDDING_ENDPOINT, "
                "EMBEDDING_API_KEY, and EMBEDDING_MODEL."
            ),
        ) from error

    return [item.embedding for item in response.data]


def save_collection(
    assistant: Assistant,
    document_text: str,
    document_filename: str,
) -> int:
    # Ingestion pipeline: split the uploaded document into overlapping
    # character chunks, embed each chunk, and persist everything needed for
    # later retrieval inside this assistant's collection-store directory.
    chunks = chunk_text(document_text)
    embeddings = embed_texts([chunk["text"] for chunk in chunks])

    records = []
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        records.append(
            {
                "id": chunk["id"],
                "text": chunk["text"],
                "embedding": embedding,
                "metadata": {
                    "assistant_id": assistant.id,
                    "document_filename": document_filename,
                    "start": chunk["start"],
                    "end": chunk["end"],
                },
            }
        )

    store_dir = collection_dir(assistant.id)
    store_dir.mkdir(parents=True, exist_ok=True)
    try:
        collection_file(assistant.id).write_text(
            json.dumps(
                {
                    "embedding_model": os.getenv(
                        "EMBEDDING_MODEL",
                        "nomic-embed-text",
                    ),
                    "chunk_size": DEFAULT_CHUNK_SIZE,
                    "chunk_overlap": DEFAULT_CHUNK_OVERLAP,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "records": records,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="Could not save the vector collection.",
        ) from error

    return len(records)


def ensure_collection(assistant: Assistant) -> None:
    if collection_file(assistant.id).exists():
        return

    legacy_document_path = assistant_dir(assistant.id) / "knowledge.txt"
    try:
        document_text = legacy_document_path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail="The assistant vector collection could not be found.",
        ) from error
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="Could not read the assistant document for ingestion.",
        ) from error

    save_collection(
        assistant=assistant,
        document_text=document_text,
        document_filename=assistant.document_filename or "knowledge.txt",
    )


def read_collection(assistant_id: str) -> list[dict[str, Any]]:
    try:
        collection = json.loads(collection_file(assistant_id).read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail="The assistant vector collection could not be found.",
        ) from error
    except (json.JSONDecodeError, OSError) as error:
        raise HTTPException(
            status_code=500,
            detail="Could not read the assistant vector collection.",
        ) from error

    return collection.get("records", [])


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)


def retrieve_chunks(assistant_id: str, question: str) -> list[dict[str, Any]]:
    # Retrieval pipeline: embed the user's question, compare it with every
    # stored chunk vector, keep the top-K chunks above the similarity threshold,
    # and return only those chunks for prompt context and debugging.
    top_k = get_int_env("TOP_K", 4)
    threshold = get_float_env("RAG_THRESHOLD", 0.50)
    records = read_collection(assistant_id)
    query_embedding = embed_texts([question])[0]

    ranked_chunks = []
    for record in records:
        similarity = cosine_similarity(query_embedding, record["embedding"])
        if similarity < threshold:
            continue

        text = record["text"]
        ranked_chunks.append(
            {
                "id": record["id"],
                "similarity": round(similarity, 4),
                "text": text,
                "preview": text[:240],
                "metadata": record.get("metadata", {}),
            }
        )

    ranked_chunks.sort(key=lambda item: item["similarity"], reverse=True)
    return ranked_chunks[:top_k]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/assistants", response_model=Assistant, status_code=201)
def create_assistant(request: AssistantCreate) -> Assistant:
    assistants = read_assistants()
    assistant = Assistant(
        id=str(uuid4()),
        created_at=datetime.now(timezone.utc).isoformat(),
        **request.model_dump(),
    )
    assistants.append(assistant)
    write_assistants(assistants)
    return assistant


@app.get("/assistants", response_model=list[Assistant])
def list_assistants() -> list[Assistant]:
    return read_assistants()


@app.delete("/assistants/{assistant_id}")
def delete_assistant(assistant_id: str) -> dict[str, str]:
    assistants = read_assistants()
    assistant = next(
        (item for item in assistants if item.id == assistant_id),
        None,
    )
    if assistant is None:
        raise HTTPException(status_code=404, detail="Assistant not found.")

    document_dir = assistants_file.parent / "assistants" / assistant.id
    try:
        if document_dir.exists():
            shutil.rmtree(document_dir)
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="Could not delete the assistant document.",
        ) from error

    remaining_assistants = [
        item for item in assistants if item.id != assistant_id
    ]
    write_assistants(remaining_assistants)
    return {"message": "Assistant deleted."}


@app.post("/assistants/chat", response_model=AssistantChatResponse)
def assistant_chat(request: AssistantChatRequest) -> AssistantChatResponse:
    assistants = read_assistants()
    assistant = next(
        (item for item in assistants if item.id == request.assistant_id),
        None,
    )
    if assistant is None:
        raise HTTPException(status_code=404, detail="Assistant not found.")
    if not assistant.has_document:
        raise HTTPException(
            status_code=400,
            detail="The selected assistant does not have a document.",
        )

    ensure_collection(assistant)
    retrieved_chunks = retrieve_chunks(assistant.id, request.message)
    context = "\n\n".join(
        f"[{chunk['id']} | similarity {chunk['similarity']}]\n{chunk['text']}"
        for chunk in retrieved_chunks
    )

    filled_prompt = (
        assistant.prompt_template
        .replace("{context}", context)
        .replace("{user_input}", request.message)
    )
    messages = [
        {"role": "system", "content": assistant.system_prompt},
        {"role": "user", "content": filled_prompt},
    ]

    endpoint = os.getenv("OPENAI_ENDPOINT")
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("MODEL")
    if not endpoint or not api_key or not model:
        raise HTTPException(status_code=500, detail="OpenAI configuration is missing.")

    client = OpenAI(base_url=endpoint, api_key=api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    choice = completion.choices[0]

    return AssistantChatResponse(
        reply=choice.message.content or "",
        assistant_id=assistant.id,
        assistant_name=assistant.name,
        filled_prompt=filled_prompt,
        messages=messages,
        retrieved_chunks=retrieved_chunks,
        usage=completion.usage.model_dump() if completion.usage else {},
        finish_reason=choice.finish_reason,
    )


@app.post("/assistants/{assistant_id}/document", response_model=Assistant)
async def upload_assistant_document(
    assistant_id: str,
    file: UploadFile = File(...),
) -> Assistant:
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="The document must be a UTF-8 .txt or .md file.",
        )

    assistants = read_assistants()
    assistant = next(
        (item for item in assistants if item.id == assistant_id),
        None,
    )
    if assistant is None:
        raise HTTPException(status_code=404, detail="Assistant not found.")

    file_bytes = await file.read()
    try:
        document_text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(
            status_code=400,
            detail="The document must contain UTF-8 plain text.",
        ) from error

    document_dir = assistant_dir(assistant.id)
    document_dir.mkdir(parents=True, exist_ok=True)
    try:
        if collection_dir(assistant.id).exists():
            shutil.rmtree(collection_dir(assistant.id))
        (document_dir / "knowledge.txt").write_text(
            document_text,
            encoding="utf-8",
        )
        (document_dir / f"knowledge{suffix}").write_text(
            document_text,
            encoding="utf-8",
        )
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="Could not save the document.",
        ) from error

    chunk_count = save_collection(
        assistant=assistant,
        document_text=document_text,
        document_filename=Path(filename).name,
    )

    assistant.has_document = True
    assistant.document_filename = Path(filename).name
    assistant.document_char_count = len(document_text)
    assistant.document_chunk_count = chunk_count
    write_assistants(assistants)
    return assistant


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    endpoint = os.getenv("OPENAI_ENDPOINT")
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("MODEL")

    if not endpoint or not api_key or not model:
        raise HTTPException(status_code=500, detail="OpenAI configuration is missing.")

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": request.message},
    ]

    client = OpenAI(base_url=endpoint, api_key=api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
    )

    choice = completion.choices[0]
    reply = choice.message.content or ""
    messages.append({"role": "assistant", "content": reply})

    return ChatResponse(
        reply=reply,
        messages=messages,
        usage=completion.usage.model_dump() if completion.usage else {},
        finish_reason=choice.finish_reason,
    )


@app.post("/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    endpoint = os.getenv("OPENAI_ENDPOINT")
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("MODEL")

    if not endpoint or not api_key or not model:
        raise HTTPException(status_code=500, detail="OpenAI configuration is missing.")

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": request.message},
    ]

    def event_stream():
        client = OpenAI(base_url=endpoint, api_key=api_key)
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
        )

        reply_parts = []
        usage = {}
        finish_reason = None

        for chunk in stream:
            if chunk.usage:
                usage = chunk.usage.model_dump()

            if not chunk.choices:
                continue

            choice = chunk.choices[0]

            if choice.finish_reason:
                finish_reason = choice.finish_reason

            content = choice.delta.content or ""
            if content:
                reply_parts.append(content)
                yield f"event: chunk\ndata: {json.dumps({'content': content})}\n\n"

        reply = "".join(reply_parts)
        completed_messages = [
            *messages,
            {"role": "assistant", "content": reply},
        ]
        done_data = {
            "reply": reply,
            "messages": completed_messages,
            "usage": usage,
            "finish_reason": finish_reason,
        }
        yield f"event: done\ndata: {json.dumps(done_data)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/chat/vision", response_model=VisionResponse)
async def chat_vision(
    prompt: str = Form(...),
    image: UploadFile = File(...),
) -> VisionResponse:
    endpoint = os.getenv("OPENAI_ENDPOINT")
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("MODEL")

    if not endpoint or not api_key or not model:
        raise HTTPException(status_code=500, detail="OpenAI configuration is missing.")

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="The uploaded file must be an image.")

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")

    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:{image.content_type};base64,{encoded_image}"
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        },
    ]

    client = OpenAI(base_url=endpoint, api_key=api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
    )

    choice = completion.choices[0]
    reply = choice.message.content or ""
    completed_messages = [
        *messages,
        {"role": "assistant", "content": reply},
    ]

    return VisionResponse(
        prompt=prompt,
        reply=reply,
        messages=completed_messages,
        usage=completion.usage.model_dump() if completion.usage else {},
        finish_reason=choice.finish_reason,
    )


app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
