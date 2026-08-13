from typing import Any
from unittest.mock import Mock, patch

import pytest

from sdk.langchain_adapter import IntentLockLangChainTool


class _FakeResp:
    def __init__(self, status: int, body: bytes) -> None:
        self._status = status
        self._body = body

    def getcode(self) -> int:
        return self._status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        return None


class _ToolWithName:
    name = "named_tool"

    def __call__(self, *args: Any, **kwargs: Any) -> str:
        return "ran"


def _returning_tool(*, result: Any = "ran") -> Mock:
    tool = Mock(return_value=result)
    tool.__name__ = "kw_tool"
    return tool


def test_name_resolution_prefers_name_attribute() -> None:
    tool = IntentLockLangChainTool(_ToolWithName())
    assert tool.tool_name == "named_tool"


def test_name_resolution_falls_back_to_class_name() -> None:
    class PlainCallable:
        def __call__(self) -> str:
            return "x"

    tool = IntentLockLangChainTool(PlainCallable())
    assert tool.tool_name == "PlainCallable"


def test_call_passes_through_on_success_and_delegates_attrs() -> None:
    inner = _returning_tool(result="ok")
    tool = IntentLockLangChainTool(inner)
    with patch("sdk.langchain_adapter.urlopen", return_value=_FakeResp(200, b"{}")):
        result = tool(1, user_prompt="prompt", agent_id="agent-9")
    assert result == "ok"
    assert tool.tool_name == "kw_tool"
    # __getattr__ delegation
    assert tool.some_method is inner.some_method


def test_call_http_error_returns_blocked_message() -> None:
    import urllib.error

    inner = _returning_tool()
    tool = IntentLockLangChainTool(inner)

    err = urllib.error.HTTPError("http://x", 403, "Forbidden", {}, None)
    err.read = lambda: b'{"detail": "Forbidden by policy"}'
    with patch("sdk.langchain_adapter.urlopen", side_effect=err):
        result = tool(1, user_prompt="p", agent_id="a")
    assert result.startswith("ACTION BLOCKED BY SECURITY POLICY:")
    assert "Forbidden by policy" in result
    inner.assert_not_called()


def test_call_http_error_without_read_attribute() -> None:
    import urllib.error

    inner = _returning_tool()
    tool = IntentLockLangChainTool(inner)
    err = urllib.error.HTTPError("http://x", 503, "Unavailable", {}, None)
    with patch("sdk.langchain_adapter.urlopen", side_effect=err):
        result = tool(1, user_prompt="p", agent_id="a")
    assert "ACTION BLOCKED BY SECURITY POLICY:" in result
    inner.assert_not_called()


def test_call_url_error_raises_runtime_error() -> None:
    import urllib.error

    tool = IntentLockLangChainTool(_returning_tool())
    with (
        patch("sdk.langchain_adapter.urlopen", side_effect=urllib.error.URLError("dn")),
        pytest.raises(RuntimeError) as exc,
    ):
        tool(1, user_prompt="p", agent_id="a")
    assert "IntentLock request failed" in str(exc.value)


def test_call_non_200_returns_blocked_message() -> None:
    tool = IntentLockLangChainTool(_returning_tool())
    with patch("sdk.langchain_adapter.urlopen", return_value=_FakeResp(500, b"boom")):
        result = tool(1, user_prompt="p", agent_id="a")
    assert result.startswith("ACTION BLOCKED BY SECURITY POLICY:")
    assert "boom" in result


def test_call_rejects_unsafe_gateway_url() -> None:
    tool = IntentLockLangChainTool(_returning_tool(), base_url="file:///tmp/not-intentlock")
    with (
        pytest.raises(ValueError, match="http or https"),
        patch("sdk.langchain_adapter.urlopen") as mock_urlopen,
    ):
        tool(1, user_prompt="p", agent_id="a")
    mock_urlopen.assert_not_called()


def test_extract_reason_handles_plain_text() -> None:
    reason = IntentLockLangChainTool._extract_reason("just text")
    assert reason == "just text"


def test_extract_reason_handles_malformed_json() -> None:
    reason = IntentLockLangChainTool._extract_reason("{not json")
    assert reason == "{not json"


def test_extract_reason_handles_json_without_detail() -> None:
    reason = IntentLockLangChainTool._extract_reason('{"code": 42}')
    assert reason == '{"code": 42}'
