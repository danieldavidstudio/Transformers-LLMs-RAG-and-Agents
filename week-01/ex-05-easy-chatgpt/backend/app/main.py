from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Easy ChatGPT API")
frontend_dir = Path(__file__).resolve().parents[2] / "frontend"


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return ChatResponse(reply="Backend connected successfully.")


app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
