# IntentLock 4.0

**Proof-of-intent authorization for AI agents.** IntentLock evaluates a proposed tool action, returns a short-lived Ed25519 execution token for permitted actions, and consumes that token exactly once.

> **Tiers:** Free | Pro ($49/seat/mo) | Business ($199/seat/mo) | Enterprise (custom)  
> See [`docs/business/PRICING.md`](docs/business/PRICING.md) for details.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green)
![License](https://img.shields.io/badge/license-Proprietary-lightgrey)
![Tests](https://img.shields.io/badge/tests-760%20passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-99.92%25-ff69b4)

## What is implemented

- Email/password registration and bearer-token authentication.
- HS256 access tokens with `iat`, `nbf`, `exp`, `jti`, token-type validation, and configurable clock-skew tolerance.
- Intent evaluation for destructive SQL, selected shell/polyglot patterns, policy-file matches, and prompt-based transfer limits.
- One-second (configurable) Ed25519 execution tokens with strict expiration and nonce replay protection.
- Composite nonce store (local memory + Redis). In production Redis is required; if Redis is unavailable, execution-token consumption fails closed.
- Authenticated HITL queue endpoints with database-backed durability and role-based approver authorization, in-memory rate limiting, correlation IDs, JSONL audit events, CORS, and response security headers.
- Authenticated intent evaluation endpoints (`/intent/verify`, `/intent/execute`) requiring bearer-token authentication via `CurrentUser`.
- SQLite for local development and PostgreSQL for production. Alembic owns the `0001_initial_schema` and `0002_add_user_role` migrations.
- Python SDK and LangChain callable wrapper. SDK gateway URLs must be HTTP(S).

## Security assumptions

- The intent verification and execution endpoints (`/intent/verify`, `/intent/execute`) require bearer-token authentication (`CurrentUser`). The SDK must provide a valid `auth_token`.
- Access tokens rely on HS256 signature validation and short expiration. They have no server-side replay protection. Rotation and high-entropy secrets are required in non-development environments.
- Execution tokens use Ed25519 signatures with atomic nonce consumption. Redis failure in production causes token consumption to fail closed.
- Rate limiting is process-local when Redis is unavailable. It is an availability control, not a distributed security boundary.
- The SDK validates gateway URLs as HTTP(S) but does not validate TLS certificates or perform network-level access control.

## Threat model

### Trust boundaries

1. **Agent → Gateway**: Intent verification and execution endpoints (`/intent/verify`, `/intent/execute`) require bearer-token authentication. The SDK must present a valid access token.
2. **User → Gateway**: Authentication endpoints (`/auth/register`, `/auth/login`) and HITL approval endpoints (`/approval/*`) require bearer-token authentication.
3. **Gateway → Redis**: Replay protection relies on atomic nonce consumption. Redis failure must fail closed in production.
4. **Gateway → Database**: User persistence, approval requests, audit events, execution token records.
5. **Gateway → External LLM/Tools**: The SDK invokes the gateway before calling protected tools; the gateway does not directly execute external actions.

### Attack surfaces

- Bearer-authenticated intent endpoints (`/intent/verify`, `/intent/execute`) requiring valid access tokens
- JWT access token validation
- Execution token signature verification and nonce consumption
- Policy engine pattern matching
- Rate limiting (proxy-aware IP extraction)
- Redis authentication and failure behavior
- Database connection and transaction handling
- Key material storage and rotation
- Audit log integrity
- Request size and malformed input handling

## Configuration

Copy `.env.example` to `.env` for development. Important variables:

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | `development`, `staging`, `production`, or `test` |
| `DEBUG` | Enables `/docs`, `/redoc`, and `/openapi.json` only when true |
| `DATABASE_URL` | SQLite locally; PostgreSQL is required when `APP_ENV=production` |
| `JWT_SECRET_KEY` | At least 32 characters; the development default is rejected outside development |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` / `JWT_CLOCK_SKEW_SECONDS` | Access-token lifetime and validation tolerance |
| `EXECUTION_TOKEN_TTL_SECONDS` | Execution-token lifetime, 1–60 seconds |
| `EXECUTION_KEY_PATH` | Optional PEM path for a stable Ed25519 execution key |
| `REDIS_URL` / `REDIS_ENABLED` | Distributed replay protection; both are required in production |
| `CORS_ORIGINS` | Comma-separated allowed browser origins |
| `RATE_LIMIT_*` | Per-minute login, registration, and intent limits |
| `HITL_TTL_SECONDS` | Database-backed approval request lifetime |
| `VELOCITY_*` | Thresholds for the reusable velocity-tracker component |

Never commit `.env`, private PEM keys, database backups, or audit logs. Use a unique high-entropy `JWT_SECRET_KEY` in every non-development environment.

## Quickstart

```bash
# 1. Clone and enter the repository
git clone https://github.com/your-org/intentlock.git
cd intentlock

# 2. Create a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -e ".[dev,security]"

# 4. Configure environment
copy .env.example .env

# 5. Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The service initializes local tables on startup. For managed deployments, apply the Alembic migration before application rollout:

```bash
alembic upgrade head
alembic check
alembic current
```

## Authentication example

```python
import httpx

response = httpx.post(
    "http://localhost:8000/api/v1/auth/register",
    json={
        "email": "agent@example.com",
        "password": "SecurePass1!",
    },
)
token = response.json()["access_token"]
```

## Authorization example

```python
from sdk.intentlock import IntentLockGuard, SecurityError

client = IntentLockGuard(
    base_url="http://localhost:8000/api/v1/intent/verify",
    execute_url="http://localhost:8000/api/v1/intent/execute",
    auth_token=token,
)

try:
    proof = client.verify_intent(
        tool_name="database_query",
        tool_arguments={"query": "SELECT * FROM users LIMIT 10"},
        user_prompt="List all active users",
        agent_id="agent-001",
    )
    print("Intent permitted:", proof)
except SecurityError as exc:
    print(f"IntentLock denied execution: {exc}")
```

## Policy example

Blocked patterns are defined in `config/policies.yaml`:

```yaml
score_threshold: 0.5
blocked_patterns:
  - "drop table"
  - "truncate table"
  - "delete from"
  - "update set"
  - "union select"
  - "information_schema"
```

The policy engine compiles patterns with regex word boundaries and flexible whitespace. Financial transfer limits can be extracted from the user prompt:

```text
User: "Send up to $500 to Alice"
Agent: transfer(to="Alice", amount=500)  # PERMITTED

User: "Send $5000 to Alice"
Agent: transfer(to="Alice", amount=5000) # DENIED — exceeds prompt limit
```

## HITL workflow example

```python
from sdk.intentlock import IntentLockGuard

client = IntentLockGuard(auth_token=token)

# List pending approval requests
pending = client.list_pending_approvals()
for request in pending.get("pending", []):
    print(f"Request {request['request_id']}: {request['intent_text']}")

# Approve a high-risk operation
client.approve_request("request-uuid-here")

# Reject a suspicious operation
client.reject_request("request-uuid-here")
```

## Error handling

| Error | Cause | Resolution |
| --- | --- | --- |
| `SecurityError: IntentLock denied execution` | Policy blocked the action, SQL injection detected, or token validation failed | Review the action, adjust policy, or obtain approval |
| `HTTP 403 Forbidden` | Action violates intent evaluation or policy rules | Check the `detail` field for the specific rejection reason |
| `HTTP 401 Unauthorized` | Invalid or expired execution token | Request a new execution token |
| `HTTP 404 Not Found` | Approval request does not exist | Verify the request ID |
| `HTTP 422 Unprocessable Entity` | Malformed request DTO | Check request body against the OpenAPI schema |

## Security boundaries

- **Bearer-authenticated intent endpoints**: `/intent/verify` and `/intent/execute` require a valid bearer token (`CurrentUser`). The SDK must provide an `auth_token`.
- **Short-lived tokens**: Execution tokens expire in 1–60 seconds. Replay is prevented by atomic nonce consumption.
- **Redis fail-closed**: Production deployments require Redis. If Redis is unavailable, nonce consumption fails and the request is denied.
- **Process-local rate limiting**: When Redis is unavailable, rate limiting falls back to in-memory counters that are not shared across instances.
- **HITL durability**: Approval requests are persisted in PostgreSQL and survive restarts.
- **Key management**: Ed25519 keys are generated in-process by default. Use `EXECUTION_KEY_PATH` to persist keys across restarts. Integrate with a KMS/HSM for production.

## API

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | No | Liveness |
| GET | `/api/v1/ready` | No | Database and configured-Redis readiness |
| POST | `/api/v1/auth/register` | No | Create a user and access token |
| POST | `/api/v1/auth/login` | No | Obtain an access token |
| GET | `/api/v1/auth/me` | Bearer | Current user |
| POST | `/api/v1/intent/verify` | Bearer | Evaluate an action and issue an execution token when allowed |
| POST | `/api/v1/intent/execute` | Bearer | Consume one execution token |
| GET | `/api/v1/approval/pending` | Bearer | List pending HITL requests |
| POST | `/api/v1/approval/{request_id}/approve` | Bearer | Approve a HITL request |
| POST | `/api/v1/approval/{request_id}/reject` | Bearer | Reject a HITL request |
| GET | `/api/v1/.well-known/jwks.json` | No | Execution-token public key |

OpenAPI is available at `/openapi.json` only when `DEBUG=true`.

## Docker

`docker compose up --build` starts the application, PostgreSQL, and Redis. Compose requires explicitly set credentials via environment variables; the application image runs as the non-root `intentlock` user with a restricted `/tmp` tmpfs mount. Persist the PostgreSQL and Redis volumes and forward `logs/audit_trail.jsonl` to centralized storage.

Example `.env` for Docker Compose:

```bash
POSTGRES_USER=intentlock
POSTGRES_PASSWORD=<secure-random-value>
REDIS_PASSWORD=<secure-random-value>
JWT_SECRET_KEY=<secure-random-value-at-least-32-chars>
```

## Verification

```bash
python -m compileall app sdk tests
ruff check app sdk tests
mypy app
pytest -q
python -m coverage run --branch -m pytest --no-cov
python -m coverage report -m
alembic check
alembic current
```

`--no-cov` prevents pytest-cov's configured inner collector from conflicting with the outer coverage command.

## Operations

Audit events are written as JSONL to `logs/audit_trail.jsonl` and include timestamps, event type, and correlation ID. Preserve those logs according to the organization's retention policy, alert on repeated policy/replay failures, rotate JWT and execution-signing material through a controlled deployment, and restore PostgreSQL/Redis from tested backups.

On an incident, restrict API ingress, rotate affected secrets, retain audit logs, investigate correlation IDs, and invalidate/redeploy signing material as appropriate. Tokens are intentionally short lived; replay attempts are denied.

## Future extension points

`KMSKeyManager` is an interface-shaped placeholder, not a configured KMS integration. Provider-backed signing, automatic key rotation, distributed rate limiting, and downstream-resource authorization are future deployment capabilities, not V4 runtime features.

V4.0 has known limitations documented in `docs/security/SECURITY_ASSURANCE_REPORT.md`. Future security patches, dependency updates, infrastructure changes, and new capabilities remain normal post-release maintenance.

## Commercial

IntentLock is available in Free, Pro, Business, and Enterprise tiers.

- **Free** — Open source, 1 agent, 100 intents/day, community support
- **Pro** — $49/seat/mo, 10 agents, 10k intents/day, SSO, priority support
- **Business** — $199/seat/mo, 100 agents, 100k intents/day, identity-based RBAC, SIEM/ticketing adapter ports, compliance exports
- **Enterprise** — Custom pricing, unlimited agents, KMS/HSM interface, 99.99% SLA, dedicated support

See [`docs/business/PRICING.md`](docs/business/PRICING.md) for full feature comparisons and [`docs/commercial/ENTERPRISE_DEPLOYMENT.md`](docs/commercial/ENTERPRISE_DEPLOYMENT.md) for production patterns.

For sales, partnerships, or enterprise inquiries: sales@intentlock.io
