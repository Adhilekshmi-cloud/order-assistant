from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


def test_chat_ok(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setattr(main, "run_agent", lambda m, h: {"reply": "hi", "steps": []})
    r = client.post("/api/chat", json={"message": "hello"})
    assert r.status_code == 200 and r.json()["reply"] == "hi"


def test_rejects_blank_and_too_long():
    assert client.post("/api/chat", json={"message": "   "}).status_code == 422
    assert client.post("/api/chat", json={"message": "a" * 501}).status_code == 422
    assert client.post("/api/chat", json={}).status_code == 422


def test_missing_key_is_503(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 503


def test_agent_failure_is_502(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "x")

    def boom(m, h):
        raise RuntimeError("llm down")

    monkeypatch.setattr(main, "run_agent", boom)
    r = client.post("/api/chat", json={"message": "hi"})
    assert r.status_code == 502 and "llm down" not in r.text