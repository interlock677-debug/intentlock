"""Tests for request size limit middleware."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.presentation.api.middleware.request_size_limit import RequestSizeLimitMiddleware


def _make_app(max_bytes: int = 1024) -> FastAPI:
    app = FastAPI()

    @app.post("/api/v1/intent/verify")
    async def verify() -> dict[str, str]:
        return {"ok": "true"}

    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=max_bytes)
    return app


def test_request_under_size_limit_accepted() -> None:
    app = _make_app(max_bytes=1024)
    client = TestClient(app)
    payload = {
        "user_prompt": "test",
        "agent_id": "a",
        "reasoning_step": "s",
        "proposed_tool": "t",
        "tool_arguments": {},
    }
    resp = client.post("/api/v1/intent/verify", json=payload)
    assert resp.status_code == 200


def test_request_over_size_limit_rejected() -> None:
    app = _make_app(max_bytes=100)
    client = TestClient(app)
    large_payload = {"data": "x" * 1000}
    resp = client.post("/api/v1/intent/verify", json=large_payload)
    assert resp.status_code == 413


def test_request_with_content_length_over_limit_rejected() -> None:
    app = _make_app(max_bytes=100)
    client = TestClient(app)
    payload = {"data": "x" * 1000}
    resp = client.post(
        "/api/v1/intent/verify",
        json=payload,
        headers={"Content-Length": "999999"},
    )
    assert resp.status_code == 413


def test_request_with_invalid_content_length_accepted() -> None:
    app = _make_app(max_bytes=1024)
    client = TestClient(app)
    payload = {
        "user_prompt": "test",
        "agent_id": "a",
        "reasoning_step": "s",
        "proposed_tool": "t",
        "tool_arguments": {},
    }
    resp = client.post(
        "/api/v1/intent/verify",
        json=payload,
        headers={"Content-Length": "not-a-number"},
    )
    assert resp.status_code == 200
