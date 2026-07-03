from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Easy ChatGPT API")


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
