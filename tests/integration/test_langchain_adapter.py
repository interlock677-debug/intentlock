from typing import Any

from sdk.langchain_adapter import IntentLockLangChainTool


class FakeResponse:
    def __init__(self, response: Any) -> None:
        self._response = response

    def getcode(self) -> int:
        return self._response.status_code

    def read(self) -> bytes:
        return self._response.content

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        return None


def test_intent_lock_langchain_tool_allows_valid_call(client, monkeypatch):
    def add_numbers(a: int, b: int, user_prompt: str = "Add two numbers", agent_id: str = "agent-000") -> int:
        return a + b

    tool = IntentLockLangChainTool(
        add_numbers,
        base_url="http://testserver/api/v1/intent/verify",
    )

    def fake_urlopen(request: Any, timeout: int = 5) -> FakeResponse:
        headers = {k: v for k, v in request.header_items()}
        response = client.post(request.get_full_url(), data=request.data, headers=headers)
        return FakeResponse(response)

    monkeypatch.setattr("sdk.langchain_adapter.urlopen", fake_urlopen)

    result = tool(2, 3, user_prompt="Add two numbers and return the result", agent_id="agent-123")

    assert result == 5


def test_intent_lock_langchain_tool_blocks_malicious_action(client, monkeypatch):
    def execute_sql(query: str, user_prompt: str = "Run SQL query", agent_id: str = "agent-000") -> str:
        return "SQL executed"

    tool = IntentLockLangChainTool(
        execute_sql,
        base_url="http://testserver/api/v1/intent/verify",
    )

    def fake_urlopen(request: Any, timeout: int = 5) -> FakeResponse:
        headers = {k: v for k, v in request.header_items()}
        response = client.post(request.get_full_url(), data=request.data, headers=headers)
        return FakeResponse(response)

    monkeypatch.setattr("sdk.langchain_adapter.urlopen", fake_urlopen)

    result = tool(
        "DROP TABLE users;",
        user_prompt="Run a harmful query",
        agent_id="agent-123",
    )

    assert result.startswith("ACTION BLOCKED BY SECURITY POLICY:")
    assert "Destructive SQL detected" in result
