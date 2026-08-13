from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from sdk.intentlock import IntentLockGuard, SecurityError, guard_tool


class FakeResponse:
    def __init__(self, status_code: int, content: bytes) -> None:
        self.status_code = status_code
        self.content = content

    def getcode(self) -> int:
        return self.status_code

    def read(self) -> bytes:
        return self.content

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        return None


def test_verify_intent_success() -> None:
    guard = IntentLockGuard()
    with patch(
        "sdk.intentlock.urlopen",
        return_value=FakeResponse(200, b'{"ephemeral_token": "tok-123"}'),
    ) as mock_urlopen:
        token = guard.verify_intent(
            tool_name="read_file",
            tool_arguments={"path": "file.txt"},
            user_prompt="Read the file",
        )
    assert token == "tok-123"
    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args.args[0]
    assert request.method == "POST"
    assert request.full_url == "http://127.0.0.1:8000/api/v1/intent/verify"


def test_verify_intent_http_error() -> None:
    import urllib.error

    guard = IntentLockGuard()
    err = urllib.error.HTTPError(
        "http://127.0.0.1:8000/api/v1/intent/verify",
        403,
        "Forbidden",
        {},
        None,
    )
    err.read = lambda: b'{"detail": "Blocked by policy"}'
    with patch("sdk.intentlock.urlopen", side_effect=err), pytest.raises(SecurityError) as exc_info:
        guard.verify_intent(
            tool_name="execute_sql",
            tool_arguments={"query": "DROP TABLE users"},
            user_prompt="Run query",
        )
    assert "403" in str(exc_info.value)
    assert "Blocked by policy" in str(exc_info.value)


def test_verify_intent_url_error() -> None:
    import urllib.error

    guard = IntentLockGuard()
    with (
        patch("sdk.intentlock.urlopen", side_effect=urllib.error.URLError("connection refused")),
        pytest.raises(SecurityError) as exc_info,
    ):
        guard.verify_intent(
            tool_name="tool",
            tool_arguments={},
            user_prompt="prompt",
        )
    assert "IntentLock request failed" in str(exc_info.value)


def test_verify_intent_non_200() -> None:
    guard = IntentLockGuard()
    with (
        patch(
            "sdk.intentlock.urlopen",
            return_value=FakeResponse(500, b"internal error"),
        ),
        pytest.raises(SecurityError) as exc_info,
    ):
        guard.verify_intent(
            tool_name="tool",
            tool_arguments={},
            user_prompt="prompt",
        )
    assert "500" in str(exc_info.value)


@pytest.mark.parametrize("url", ["file:///tmp/not-intentlock", "http://"])
def test_verify_intent_rejects_unsafe_gateway_url(url: str) -> None:
    guard = IntentLockGuard(base_url=url)
    with (
        pytest.raises(ValueError, match="http or https"),
        patch("sdk.intentlock.urlopen") as mock_urlopen,
    ):
        guard.verify_intent(tool_name="tool", tool_arguments={}, user_prompt="prompt")
    mock_urlopen.assert_not_called()


def test_verify_intent_missing_token() -> None:
    guard = IntentLockGuard()
    with (
        patch(
            "sdk.intentlock.urlopen",
            return_value=FakeResponse(200, b'{"status": "ok"}'),
        ),
        pytest.raises(SecurityError) as exc_info,
    ):
        guard.verify_intent(
            tool_name="tool",
            tool_arguments={},
            user_prompt="prompt",
        )
    assert "did not return an ephemeral execution token" in str(exc_info.value)


def test_consume_execution_token_success() -> None:
    guard = IntentLockGuard()
    with patch(
        "sdk.intentlock.urlopen",
        return_value=FakeResponse(200, b'{"status": "executed", "agent_id": "agent-1"}'),
    ) as mock_urlopen:
        result = guard.consume_execution_token("tok-123")
    assert result == {"status": "executed", "agent_id": "agent-1"}
    request = mock_urlopen.call_args.args[0]
    assert request.full_url == "http://127.0.0.1:8000/api/v1/intent/execute"


def test_consume_execution_token_http_error() -> None:
    import urllib.error

    guard = IntentLockGuard()
    err = urllib.error.HTTPError(
        "http://127.0.0.1:8000/api/v1/intent/execute",
        401,
        "Unauthorized",
        {},
        None,
    )
    err.read = lambda: b'{"detail": "replayed token"}'
    with patch("sdk.intentlock.urlopen", side_effect=err), pytest.raises(SecurityError) as exc_info:
        guard.consume_execution_token("tok-123")
    assert "execution failed" in str(exc_info.value)
    assert "replayed token" in str(exc_info.value)


def test_consume_execution_token_url_error() -> None:
    import urllib.error

    guard = IntentLockGuard()
    with (
        patch("sdk.intentlock.urlopen", side_effect=urllib.error.URLError("down")),
        pytest.raises(SecurityError) as exc_info,
    ):
        guard.consume_execution_token("tok-123")
    assert "execution request failed" in str(exc_info.value)


def test_consume_execution_token_non_200() -> None:
    guard = IntentLockGuard()
    with (
        patch(
            "sdk.intentlock.urlopen",
            return_value=FakeResponse(500, b"boom"),
        ),
        pytest.raises(SecurityError) as exc_info,
    ):
        guard.consume_execution_token("tok-123")
    assert "500" in str(exc_info.value)


def test_guard_tool_decorator_success() -> None:
    guard = IntentLockGuard()

    def mock_verify(
        tool_name: str, tool_arguments: dict[str, Any], user_prompt: str, agent_id: str
    ) -> str:
        assert tool_name == "add_numbers"
        assert tool_arguments == {"a": 2, "b": 3}
        assert user_prompt == "Add two numbers"
        assert agent_id == "agent-7"
        return "tok-5"

    def mock_consume(token: str) -> dict[str, Any]:
        assert token == "tok-5"
        return {"status": "executed"}

    with (
        patch.object(guard, "verify_intent", side_effect=mock_verify),
        patch.object(guard, "consume_execution_token", side_effect=mock_consume),
    ):

        @guard_tool(guard)
        def add_numbers(
            a: int, b: int, user_prompt: str = "Add two numbers", agent_id: str = "agent-000"
        ) -> int:
            return a + b

        result = add_numbers(2, 3, user_prompt="Add two numbers", agent_id="agent-7")

    assert result == 5


def test_guard_tool_decorator_default_prompt_and_agent() -> None:
    guard = IntentLockGuard()

    def mock_verify(
        tool_name: str, tool_arguments: dict[str, Any], user_prompt: str, agent_id: str
    ) -> str:
        assert user_prompt == "Agent tool execution request"
        assert agent_id == "agent-000"
        return "tok-5"

    with (
        patch.object(guard, "verify_intent", side_effect=mock_verify),
        patch.object(guard, "consume_execution_token", return_value={"status": "executed"}),
    ):

        @guard_tool(guard)
        def ping() -> str:
            return "pong"

        result = ping()

    assert result == "pong"


def test_guard_tool_preserves_wrapped_metadata() -> None:
    guard = IntentLockGuard()
    with (
        patch.object(guard, "verify_intent", return_value="tok-1"),
        patch.object(guard, "consume_execution_token", return_value={"status": "executed"}),
    ):

        @guard_tool(guard)
        def documented_tool() -> None:
            """Documented tool."""

        assert documented_tool.__name__ == "documented_tool"
        assert documented_tool.__doc__ == "Documented tool."
