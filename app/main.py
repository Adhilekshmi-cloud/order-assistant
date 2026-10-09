import logging
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

import groq  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field, field_validator  # noqa: E402

from .agent import run_agent  # noqa: E402

log = logging.getLogger("order-assistant")
STATIC = Path(__file__).resolve().parent.parent / "static"
app = FastAPI(title="Order Assistant")


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    history: list[Turn] = Field(default_factory=list, max_length=12)

    @field_validator("message")
    @classmethod
    def not_blank(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("message must not be blank")
        return v


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(503, "Server is missing its LLM API key.")
    try:
        return run_agent(req.message, [t.model_dump() for t in req.history])
    except groq.RateLimitError:
        raise HTTPException(429, "The assistant is rate-limited. Try again in a minute.")
    except Exception:
        log.exception("agent failed")
        raise HTTPException(502, "The assistant could not answer right now. Please try again.")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")