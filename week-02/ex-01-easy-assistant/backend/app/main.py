import base64
import json
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
from pydantic import BaseModel, field_validator

app = FastAPI(title="Easy ChatGPT API")
project_dir = Path(__file__).resolve().parents[2]
frontend_dir = project_dir / "frontend"
assistants_file = project_dir / "data" / "assistants.json"
load_dotenv(project_dir / ".env")


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

    document_path = (
        assistants_file.parent
        / "assistants"
        / assistant.id
        / "knowledge.txt"
    )
    try:
        document_text = document_path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail="The assistant document could not be found.",
        ) from error
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="Could not read the assistant document.",
        ) from error

    filled_prompt = (
        assistant.prompt_template
        .replace("{context}", document_text)
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
        usage=completion.usage.model_dump() if completion.usage else {},
        finish_reason=choice.finish_reason,
    )


@app.post("/assistants/{assistant_id}/document", response_model=Assistant)
async def upload_assistant_document(
    assistant_id: str,
    file: UploadFile = File(...),
) -> Assistant:
    filename = file.filename or ""
    if file.content_type != "text/plain" or Path(filename).suffix.lower() != ".txt":
        raise HTTPException(
            status_code=400,
            detail="The document must be a plain-text .txt file.",
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

    document_dir = assistants_file.parent / "assistants" / assistant.id
    document_dir.mkdir(parents=True, exist_ok=True)
    try:
        (document_dir / "knowledge.txt").write_text(
            document_text,
            encoding="utf-8",
        )
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="Could not save the document.",
        ) from error

    assistant.has_document = True
    assistant.document_filename = Path(filename).name
    assistant.document_char_count = len(document_text)
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
