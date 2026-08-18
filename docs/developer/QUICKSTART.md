# Developer Quickstart

Get IntentLock running locally in 5 minutes.

## Prerequisites

- Python 3.11+
- pip
- (Optional) Docker and Docker Compose for containerized deployment
- (Optional) Redis for production-like replay protection

## Option A: pip install (fastest)

```bash
python -m venv .venv
.venv\Scripts\activate

pip install intentlock
```

## Option B: Clone and install editable

```bash
git clone https://github.com/your-org/intentlock.git
cd intentlock

python -m venv .venv
.venv\Scripts\activate

pip install -e ".[dev,security]"
```

## Configure environment

Copy `.env.example` to `.env`:

```bash
copy .env.example .env
```

For local development, SQLite is used by default. Set a unique `JWT_SECRET_KEY` in every non-development environment.

## Run the gateway

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify it is running:

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok"}

curl http://localhost:8000/api/v1/ready
# {"status":"ready","db":"ok","redis":"disabled"}
```

## Register a user and get a token

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"agent@example.com\",\"password\":\"SecurePass1!\"}"
```

Save the `access_token` from the response.

## Verify an intent from Python

```python
from sdk.intentlock import IntentLockGuard, SecurityError

client = IntentLockGuard(
    base_url="http://localhost:8000/api/v1/intent/verify",
    execute_url="http://localhost:8000/api/v1/intent/execute",
    auth_token="<access_token>",
)

try:
    token = client.verify_intent(
        tool_name="database_query",
        tool_arguments={"query": "SELECT * FROM users LIMIT 10"},
        user_prompt="List all active users",
        agent_id="agent-001",
    )
    print("Intent permitted. Execution token:", token)

    result = client.consume_execution_token(token)
    print("Token consumed:", result)
except SecurityError as exc:
    print(f"Blocked: {exc}")
```

## Protect a tool with the decorator

```python
from sdk.intentlock import IntentLockGuard, guard_tool

client = IntentLockGuard(
    base_url="http://localhost:8000/api/v1/intent/verify",
    execute_url="http://localhost:8000/api/v1/intent/execute",
    auth_token="<access_token>",
)

@guard_tool(client)
def query_database(query: str, user_prompt: str = "Database query", agent_id: str = "agent-001") -> str:
    return f"Results for: {query}"

result = query_database(query="SELECT * FROM users", user_prompt="List users")
print(result)
```

## Run the demo

```bash
python examples/demo_agent_defense.py
```

## Run tests

```bash
pytest -q
```

## Next steps

- Read the [SDK reference](sdk/README.md)
- Explore [examples](EXAMPLES.md)
- Configure [policies](config/policies.yaml)
- Read the [architecture docs](../architecture/ARCHITECTURE.md)
- Deploy with [Docker Compose](../../docker-compose.yml)
