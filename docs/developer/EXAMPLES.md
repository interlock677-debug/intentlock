# Developer Examples

Advanced usage patterns for the IntentLock SDK and gateway.

## Contents

- [Multi-agent workflows](#multi-agent-workflows)
- [Custom policy rules](#custom-policy-rules)
- [Docker Compose deployment](#docker-compose-deployment)
- [LangChain tool integration](#langchain-tool-integration)
- [Human-in-the-loop approval flow](#human-in-the-loop-approval-flow)
- [Error handling and retries](#error-handling-and-retries)
- [Environment-based configuration](#environment-based-configuration)
- [Custom tool argument validation](#custom-tool-argument-validation)

---

## Multi-agent workflows

Each agent can have its own `IntentLockGuard` with a distinct `agent_id`.

```python
from sdk.intentlock import IntentLockGuard, SecurityError

agents = {
    "analyst": IntentLockGuard(
        base_url="http://localhost:8000/api/v1/intent/verify",
        execute_url="http://localhost:8000/api/v1/intent/execute",
        auth_token="<access_token>",
    ),
    "admin": IntentLockGuard(
        base_url="http://localhost:8000/api/v1/intent/verify",
        execute_url="http://localhost:8000/api/v1/intent/execute",
        auth_token="<admin_token>",
    ),
}

for agent_id, client in agents.items():
    try:
        token = client.verify_intent(
            tool_name="database_query",
            tool_arguments={"query": "SELECT * FROM users LIMIT 10"},
            user_prompt="List active users",
            agent_id=agent_id,
        )
        result = client.consume_execution_token(token)
        print(f"[{agent_id}] {result}")
    except SecurityError as exc:
        print(f"[{agent_id}] Blocked: {exc}")
```

## Custom policy rules

Edit `config/policies.yaml` to add or modify rules. The central policy engine supports versioned rules with precedence, conditions, and rollback.

```yaml
policy_version: "2"
default_effect: allow

rules:
  - id: "deny-drop-table"
    version: "2"
    effect: deny
    description: "Block DROP TABLE for non-admin agents"
    match:
      tool: "execute_sql"
      agent_id:
        - "agent-001"
        - "agent-002"
    conditions:
      - field: "tool_arguments.query"
        operator: contains
        value: "DROP TABLE"
    priority: 100

  - id: "require-approval-for-pii"
    version: "1"
    effect: require_hitl
    description: "Require human approval when querying PII tables"
    match:
      tool: "execute_sql"
    conditions:
      - field: "tool_arguments.query"
        operator: contains_any
        value:
          - "ssn"
          - "credit_card"
          - "salary"
    priority: 50
```

Reload policies without restarting the gateway by sending a `POST` to the admin policy endpoint (enterprise tier).

## Docker Compose deployment

```bash
# 1. Copy environment file
copy .env.example .env

# 2. Start all services
docker compose up --build

# 3. Verify
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/ready

# 4. Apply migrations
docker compose exec app alembic upgrade head
```

## LangChain tool integration

Wrap any callable with `IntentLockLangChainTool`.

```python
from langchain_core.tools import tool
from sdk.langchain_adapter import IntentLockLangChainTool
from sdk.intentlock import IntentLockGuard

client = IntentLockGuard(
    base_url="http://localhost:8000/api/v1/intent/verify",
    execute_url="http://localhost:8000/api/v1/intent/execute",
    auth_token="<access_token>",
)

@tool
def search_kb(query: str) -> str:
    """Search the internal knowledge base."""
    return f"Results for: {query}"

locked_tool = IntentLockLangChainTool(
    tool=search_kb,
    base_url="http://localhost:8000/api/v1/intent/verify",
    auth_token="<access_token>",
)

result = locked_tool("How do I reset my password?")
print(result)
```

## Human-in-the-loop approval flow

```python
from sdk.intentlock import IntentLockGuard, SecurityError

client = IntentLockGuard(auth_token="<approver_token>")

# 1. Agent requests an action that triggers HITL
token = client.verify_intent(
    tool_name="transfer_funds",
    tool_arguments={"amount": 5000, "to": "vendor-123"},
    user_prompt="Pay the vendor invoice",
    agent_id="billing-agent",
)
# verify_intent returns a token but does NOT consume it when policy returns require_hitl

# 2. Approver lists pending requests
pending = client.list_pending_approvals()
print(f"Pending: {len(pending.get('pending', []))}")

# 3. Approver reviews and approves
for request in pending.get("pending", []):
    if request["intent_text"].startswith("transfer_funds"):
        client.approve_request(request["request_id"])
        print(f"Approved {request['request_id']}")

# 4. Agent consumes the token after approval
result = client.consume_execution_token(token)
print(result)
```

## Error handling and retries

```python
import time
from sdk.intentlock import IntentLockGuard, SecurityError
from urllib.error import HTTPError, URLError

client = IntentLockGuard(
    base_url="http://localhost:8000/api/v1/intent/verify",
    execute_url="http://localhost:8000/api/v1/intent/execute",
    auth_token="<access_token>",
)

def verify_with_retry(tool_name, tool_arguments, user_prompt, agent_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.verify_intent(
                tool_name=tool_name,
                tool_arguments=tool_arguments,
                user_prompt=user_prompt,
                agent_id=agent_id,
            )
        except SecurityError as exc:
            if "429" in str(exc) and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError("Max retries exceeded")

try:
    token = verify_with_retry(
        tool_name="api_call",
        tool_arguments={"endpoint": "/data"},
        user_prompt="Fetch latest metrics",
        agent_id="monitoring-agent",
    )
    result = client.consume_execution_token(token)
except SecurityError as exc:
    print(f"IntentLock blocked the action: {exc}")
except (HTTPError, URLError) as exc:
    print(f"Network error: {exc}")
```

## Environment-based configuration

```python
import os
from sdk.intentlock import IntentLockGuard

env = os.getenv("APP_ENV", "development")

config = {
    "development": {
        "base_url": "http://localhost:8000/api/v1/intent/verify",
        "execute_url": "http://localhost:8000/api/v1/intent/execute",
    },
    "staging": {
        "base_url": "https://intentlock.staging.example.com/api/v1/intent/verify",
        "execute_url": "https://intentlock.staging.example.com/api/v1/intent/execute",
    },
    "production": {
        "base_url": "https://intentlock.prod.example.com/api/v1/intent/verify",
        "execute_url": "https://intentlock.prod.example.com/api/v1/intent/execute",
    },
}

client = IntentLockGuard(
    base_url=config[env]["base_url"],
    execute_url=config[env]["execute_url"],
    auth_token=os.getenv("INTENTLOCK_ACCESS_TOKEN"),
)
```

## Custom tool argument validation

The gateway validates tool arguments for SQL injection, SSRF, path traversal, and unsafe URL schemes. You can add application-specific validation before calling the gateway.

```python
from sdk.intentlock import IntentLockGuard, SecurityError

client = IntentLockGuard(
    base_url="http://localhost:8000/api/v1/intent/verify",
    execute_url="http://localhost:8000/api/v1/intent/execute",
    auth_token="<access_token>",
)

def safe_send_email(to: str, subject: str, body: str, user_prompt: str, agent_id: str) -> str:
    if not to.endswith("@example.com"):
        raise ValueError("Emails may only be sent to @example.com addresses")
    if len(body) > 10_000:
        raise ValueError("Email body exceeds 10,000 characters")

    token = client.verify_intent(
        tool_name="send_email",
        tool_arguments={"to": to, "subject": subject, "body": body},
        user_prompt=user_prompt,
        agent_id=agent_id,
    )
    result = client.consume_execution_token(token)
    return result.get("message", "Sent")

try:
    result = safe_send_email(
        to="user@example.com",
        subject="Weekly report",
        body="...",
        user_prompt="Send the weekly report to the team",
        agent_id="email-agent",
    )
    print(result)
except SecurityError as exc:
    print(f"Blocked by policy: {exc}")
except ValueError as exc:
    print(f"Local validation failed: {exc}")
```
