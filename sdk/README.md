# IntentLock SDK

Python SDK and LangChain wrapper for the IntentLock proof-of-intent authorization gateway.

## Installation

```bash
pip install intentlock
```

For development:

```bash
git clone https://github.com/your-org/intentlock.git
cd intentlock
pip install -e ".[dev,security]"
```

## Quickstart

```python
from sdk.intentlock import IntentLockGuard, SecurityError

client = IntentLockGuard(
    base_url="http://localhost:8000/api/v1/intent/verify",
    execute_url="http://localhost:8000/api/v1/intent/execute",
    auth_token="your-access-token",
)

try:
    token = client.verify_intent(
        tool_name="database_query",
        tool_arguments={"query": "SELECT * FROM users"},
        user_prompt="List all active users",
        agent_id="agent-001",
    )
    result = client.consume_execution_token(token)
    print("Intent verified and token consumed:", result)
except SecurityError as exc:
    print(f"IntentLock denied execution: {exc}")
```

## Protect tools with the decorator

```python
from sdk.intentlock import IntentLockGuard, guard_tool

client = IntentLockGuard(
    base_url="http://localhost:8000/api/v1/intent/verify",
    execute_url="http://localhost:8000/api/v1/intent/execute",
    auth_token="your-access-token",
)

@guard_tool(client)
def query_database(query: str, user_prompt: str = "Database query", agent_id: str = "agent-001") -> str:
    return f"Results for: {query}"

result = query_database(query="SELECT * FROM users", user_prompt="List users")
print(result)
```

## LangChain integration

```python
from sdk.langchain_adapter import IntentLockLangChainTool
from sdk.intentlock import IntentLockGuard

client = IntentLockGuard(
    base_url="http://localhost:8000/api/v1/intent/verify",
    execute_url="http://localhost:8000/api/v1/intent/execute",
    auth_token="your-access-token",
)

def my_tool(query: str) -> str:
    return f"Results for: {query}"

locked = IntentLockLangChainTool(
    tool=my_tool,
    base_url="http://localhost:8000/api/v1/intent/verify",
    auth_token="your-access-token",
)

result = locked("SELECT * FROM users")
print(result)
```

## Authentication

The SDK supports optional bearer-token authentication for endpoints that require it (e.g., HITL approval workflows).

```python
client = IntentLockGuard(auth_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")

# /intent/verify and /intent/execute require a valid auth_token (bearer token)
# /approval/* endpoints also require a valid bearer token
```

## HITL Workflow

Human-in-the-loop approval requires an authenticated bearer token.

```python
client = IntentLockGuard(auth_token="user-access-token")

# List pending approval requests
pending = client.list_pending_approvals()
print(f"Pending approvals: {len(pending.get('pending', []))}")

# Approve or reject by request_id
client.approve_request("request-uuid-here")
client.reject_request("request-uuid-here")
```

## Error Handling

All gateway errors raise `SecurityError`.

```python
from sdk.intentlock import IntentLockGuard, SecurityError
from urllib.error import HTTPError, URLError

client = IntentLockGuard(
    base_url="http://localhost:8000/api/v1/intent/verify",
    execute_url="http://localhost:8000/api/v1/intent/execute",
    auth_token="your-access-token",
)

try:
    token = client.verify_intent(
        tool_name="dangerous_tool",
        tool_arguments={"cmd": "rm -rf /"},
        user_prompt="Clean up files",
    )
except SecurityError as exc:
    print(f"Security error: {exc}")
except (HTTPError, URLError) as exc:
    print(f"Network error: {exc}")
```

## Security Boundaries

- The SDK validates that the gateway URL uses HTTP or HTTPS.
- Execution tokens are single-use; always call `consume_execution_token` before invoking the wrapped tool.
- The SDK does not cache or batch gateway requests.
- Gateway URLs must be reachable from the runtime environment; private network addresses are not blocked by the SDK.

## Multi-agent configuration

```python
agents = {
    "agent-001": IntentLockGuard(
        base_url="http://localhost:8000/api/v1/intent/verify",
        execute_url="http://localhost:8000/api/v1/intent/execute",
        auth_token="token-for-agent-1",
    ),
    "agent-002": IntentLockGuard(
        base_url="http://localhost:8000/api/v1/intent/verify",
        execute_url="http://localhost:8000/api/v1/intent/execute",
        auth_token="token-for-agent-2",
    ),
}

for agent_id, client in agents.items():
    token = client.verify_intent(
        tool_name="api_call",
        tool_arguments={"endpoint": "/data"},
        user_prompt="Fetch data",
        agent_id=agent_id,
    )
    client.consume_execution_token(token)
```

## API Reference

### `IntentLockGuard`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | `http://127.0.0.1:8000/api/v1/intent/verify` | Gateway verification endpoint |
| `execute_url` | `str` | `http://127.0.0.1:8000/api/v1/intent/execute` | Gateway execution endpoint |
| `auth_token` | `str \| None` | `None` | Bearer token for authenticated endpoints |

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `verify_intent` | `(tool_name, tool_arguments, user_prompt, agent_id) -> str` | Evaluate intent and return execution token |
| `consume_execution_token` | `(token) -> dict` | Consume token and return execution result |
| `guard_tool` | `(client) -> Callable` | Decorator to wrap tools with intent verification |

### `IntentLockLangChainTool`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tool` | `Callable` | required | The underlying tool to wrap |
| `base_url` | `str` | `http://127.0.0.1:8000/api/v1/intent/verify` | Gateway verification endpoint |
| `auth_token` | `str \| None` | `None` | Bearer token for authenticated endpoints |

## Development

```bash
# Run tests
pytest tests/unit/test_sdk_guard.py tests/unit/test_sdk_langchain_adapter.py

# Lint
ruff check sdk

# Type check
mypy sdk
```

## Resources

- [Quickstart](../developer/QUICKSTART.md)
- [Examples](../developer/EXAMPLES.md)
- [Architecture](../architecture/ARCHITECTURE.md)
- [Security Report](../security/SECURITY_ASSURANCE_REPORT.md)
