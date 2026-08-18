import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from sdk.intentlock import IntentLockGuard, SecurityError, guard_tool


def test_validate_gateway_url_valid_http() -> None:
    from sdk.intentlock import _validate_gateway_url

    assert _validate_gateway_url("http://localhost:8000/api/v1/intent/verify") == "http://localhost:8000/api/v1/intent/verify"


def test_validate_gateway_url_valid_https() -> None:
    from sdk.intentlock import _validate_gateway_url

    assert _validate_gateway_url("https://gateway.example.com/api") == "https://gateway.example.com/api"


def test_validate_gateway_url_invalid_scheme() -> None:
    from sdk.intentlock import _validate_gateway_url

    with pytest.raises(ValueError, match="http or https"):
        _validate_gateway_url("ftp://server/api")


def test_validate_gateway_url_missing_host() -> None:
    from sdk.intentlock import _validate_gateway_url

    with pytest.raises(ValueError, match="http or https"):
        _validate_gateway_url("http:///api")


def test_auth_headers_with_token() -> None:
    client = IntentLockGuard(auth_token="test-token")
    headers = client._auth_headers()
    assert headers["Authorization"] == "Bearer test-token"
    assert headers["Content-Type"] == "application/json"


def test_auth_headers_without_token() -> None:
    client = IntentLockGuard(auth_token=None)
    headers = client._auth_headers()
    assert "Authorization" not in headers
    assert headers["Content-Type"] == "application/json"


def test_verify_intent_success() -> None:
    client = IntentLockGuard()
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.read.return_value = json.dumps({"ephemeral_token": "token-123"}).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    with patch("sdk.intentlock.urlopen", return_value=mock_response):
        token = client.verify_intent(
            tool_name="search",
            tool_arguments={"query": "test"},
            user_prompt="search for test",
            agent_id="agent-1",
        )
    assert token == "token-123"


def test_verify_intent_denied() -> None:
    client = IntentLockGuard()
    mock_response = MagicMock()
    mock_response.getcode.return_value = 403
    mock_response.read.return_value = b"forbidden"
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    error = HTTPError("url", 403, "forbidden", {}, None)
    with patch("sdk.intentlock.urlopen", side_effect=error), pytest.raises(
        SecurityError, match="403"
    ):
            client.verify_intent(
                tool_name="search",
                tool_arguments={"query": "test"},
                user_prompt="search",
            )


def test_verify_intent_network_error() -> None:
    client = IntentLockGuard()
    with patch("sdk.intentlock.urlopen", side_effect=URLError("connection refused")), pytest.raises(
        SecurityError, match="request failed"
    ):
            client.verify_intent(
                tool_name="search",
                tool_arguments={"query": "test"},
                user_prompt="search",
            )


def test_verify_intent_missing_token() -> None:
    client = IntentLockGuard()
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.read.return_value = json.dumps({}).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    with patch("sdk.intentlock.urlopen", return_value=mock_response), pytest.raises(
        SecurityError, match="did not return"
    ):
            client.verify_intent(
                tool_name="search",
                tool_arguments={"query": "test"},
                user_prompt="search",
            )


def test_consume_execution_token_success() -> None:
    client = IntentLockGuard()
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.read.return_value = json.dumps({"status": "consumed"}).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    with patch("sdk.intentlock.urlopen", return_value=mock_response):
        result = client.consume_execution_token("token-123")
    assert result["status"] == "consumed"


def test_consume_execution_token_http_error() -> None:
    client = IntentLockGuard()
    error = HTTPError("url", 400, "bad request", {}, None)
    with patch("sdk.intentlock.urlopen", side_effect=error), pytest.raises(
        SecurityError, match="400"
    ):
            client.consume_execution_token("token-123")


def test_list_pending_approvals_success() -> None:
    client = IntentLockGuard(
        base_url="http://localhost:8000/api/v1/intent/verify",
    )
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.read.return_value = json.dumps({"requests": []}).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    with patch("sdk.intentlock.urlopen", return_value=mock_response):
        result = client.list_pending_approvals()
    assert result["requests"] == []


def test_list_pending_approvals_network_error() -> None:
    client = IntentLockGuard()
    with patch("sdk.intentlock.urlopen", side_effect=URLError("timeout")), pytest.raises(
        SecurityError, match="Approval list request failed"
    ):
            client.list_pending_approvals()


def test_approve_request_success() -> None:
    client = IntentLockGuard()
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.read.return_value = json.dumps({"status": "approved"}).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    with patch("sdk.intentlock.urlopen", return_value=mock_response):
        result = client.approve_request("req-123")
    assert result["status"] == "approved"


def test_reject_request_success() -> None:
    client = IntentLockGuard()
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.read.return_value = json.dumps({"status": "rejected"}).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    with patch("sdk.intentlock.urlopen", return_value=mock_response):
        result = client.reject_request("req-123")
    assert result["status"] == "rejected"


def test_guard_tool_decorator() -> None:
    client = IntentLockGuard()
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.read.return_value = json.dumps({"ephemeral_token": "token-123"}).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    call_count = 0

    @guard_tool(client)
    def my_tool(query: str, user_prompt: str = "default", agent_id: str = "agent-1") -> str:
        nonlocal call_count
        call_count += 1
        return f"result for {query}"

    with patch("sdk.intentlock.urlopen", return_value=mock_response):
        result = my_tool("SELECT 1", user_prompt="run query", agent_id="agent-1")
    assert result == "result for SELECT 1"
    assert call_count == 1


def test_verify_intent_non_200_status() -> None:
    client = IntentLockGuard()
    mock_response = MagicMock()
    mock_response.getcode.return_value = 500
    mock_response.read.return_value = b"server error"
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    with patch("sdk.intentlock.urlopen", return_value=mock_response), pytest.raises(
        SecurityError, match="500"
    ):
        client.verify_intent(
            tool_name="search",
            tool_arguments={"query": "test"},
            user_prompt="search",
        )


def test_consume_execution_token_network_error() -> None:
    client = IntentLockGuard()
    with patch("sdk.intentlock.urlopen", side_effect=URLError("timeout")), pytest.raises(
        SecurityError, match="execution request failed"
    ):
        client.consume_execution_token("token-123")


def test_consume_execution_token_non_200_status() -> None:
    client = IntentLockGuard()
    mock_response = MagicMock()
    mock_response.getcode.return_value = 403
    mock_response.read.return_value = b"forbidden"
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    with patch("sdk.intentlock.urlopen", return_value=mock_response), pytest.raises(
        SecurityError, match="403"
    ):
        client.consume_execution_token("token-123")


def test_list_pending_approvals_http_error() -> None:
    client = IntentLockGuard()
    error = HTTPError("url", 403, "forbidden", {}, None)
    with patch("sdk.intentlock.urlopen", side_effect=error), pytest.raises(
        SecurityError, match="Failed to list approvals"
    ):
        client.list_pending_approvals()


def test_approve_request_http_error() -> None:
    client = IntentLockGuard()
    error = HTTPError("url", 403, "forbidden", {}, None)
    with patch("sdk.intentlock.urlopen", side_effect=error), pytest.raises(
        SecurityError, match="Failed to approve request"
    ):
        client.approve_request("req-123")


def test_reject_request_network_error() -> None:
    client = IntentLockGuard()
    with patch("sdk.intentlock.urlopen", side_effect=URLError("timeout")), pytest.raises(
        SecurityError, match="Reject request failed"
    ):
        client.reject_request("req-123")
