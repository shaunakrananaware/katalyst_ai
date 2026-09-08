"""Local demo API. Sessions and source graph are process-local; run one worker."""

import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from backend.agent import Agent, ConfigurationError, ProviderError

app = FastAPI(title="Katalyst Sales Memory", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
agent = Agent()


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$")
    message: str = Field(min_length=1, max_length=8000)

    @field_validator("message")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value.strip()


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict]


@app.get("/health")
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "gemini_configured": bool(os.getenv("GOOGLE_API_KEY")),
        "model": os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
    }


@app.post("/chat", response_model=ChatResponse)
@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        return agent.chat(request.session_id, request.message)
    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# Keep this mount after the API routes so /api/* is handled by FastAPI first.
frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
app.mount(
    "/",
    StaticFiles(directory=frontend_dist, html=True, check_dir=False),
    name="frontend",
)
