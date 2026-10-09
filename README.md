# Order Assistant

A chat assistant that answers questions about an online store's orders (60 orders, June to September 2026) by calling tools over the dataset.

**Live URL:** https://order-assistant-ltrn.onrender.com/

The app runs on Render's free tier, so the first request after a period of inactivity can take up to a minute while the service wakes up.

## Tech stack

- Backend: Python, FastAPI, Pydantic
- Agent: Groq API (GPT-OSS 120B) with native tool calling
- Frontend: plain HTML, CSS and JavaScript, served by FastAPI
- Tests: pytest
- Hosting: Render

## Run locally

```
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Add your Groq API key to `.env` before starting, then open http://localhost:8000.

## Tests

```
pytest -q
```

Twelve tests cover the tools (lookup, filters, aggregation, missing IDs, bad arguments, loading the real CSV) and the API (validation, missing key, agent failure).

## API

`POST /api/chat`

Request: `{"message": "...", "history": [{"role": "user", "content": "..."}]}`

Response: `{"reply": "...", "steps": [{"tool": "...", "args": {}, "ok": true}]}`

Errors: 422 invalid input, 429 rate limited, 502 agent failure, 503 missing API key, 504 AI service unreachable.

## Project layout

- `app/main.py`: API endpoint, validation, error handling
- `app/agent.py`: tool-calling loop and system prompt
- `app/tools.py`: `get_order`, `search_orders`, `aggregate_orders`
- `static/index.html`: chat UI
- `data/orders.csv`: dataset
- `tests/`: pytest suite

## Deployment

One Render web service runs FastAPI, which serves both the API and the frontend. Build command: `pip install -r requirements.txt`. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. The Groq API key is set as an environment variable on Render and is not in the repository.