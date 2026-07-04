import base64
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel

app = FastAPI(title="Easy ChatGPT API")
project_dir = Path(__file__).resolve().parents[2]
frontend_dir = project_dir / "frontend"
load_dotenv(project_dir / ".env")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    messages: list[dict[str, str]]
    usage: dict[str, Any]
    finish_reason: str | None


class VisionResponse(BaseModel):
    prompt: str
    reply: str
    messages: list[dict[str, Any]]
    usage: dict[str, Any]
    finish_reason: str | None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
