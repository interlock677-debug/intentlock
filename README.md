# IntentLock 4.0

IntentLock is a FastAPI proof-of-intent gateway for Python AI-agent tools. It evaluates a proposed action, returns a short-lived Ed25519 execution token for permitted actions, and consumes that token exactly once.

## What is implemented

- Email/password registration and bearer-token authentication.
- HS256 access tokens with `iat`, `nbf`, `exp`, `jti`, token-type validation, and configurable clock-skew tolerance.
- Intent evaluation for destructive SQL, selected shell/polyglot patterns, policy-file matches, and prompt-based transfer limits.
- One-second (configurable) Ed25519 execution tokens with strict expiration and nonce replay protection.
- Local-memory plus Redis nonce storage. In production Redis is required; if Redis is unavailable, execution-token consumption fails closed.
- Authenticated HITL queue endpoints, in-memory rate limiting, correlation IDs, JSONL audit events, CORS, and response security headers.
- SQLite for local development and PostgreSQL for production. Alembic owns the `0001_initial_schema` migration.
- Python SDK and LangChain callable wrapper. SDK gateway URLs must be HTTP(S).

## Trust boundaries and failure behavior

The gateway evaluates an agent-supplied action before a protected tool is called. An execution token carries the agent ID and tool name, and is rejected when malformed, expired, wrong-typed, or replayed. Redis-backed nonce consumption is the distributed replay boundary; production configuration rejects disabled Redis and nonce consumption denies requests if Redis fails.

Intent verification is a policy decision, not execution of the proposed tool. The SDK calls `/intent/verify`, consumes the returned token at `/intent/execute`, and only then invokes the wrapped local callable. Deploy the API behind network controls appropriate for the agents allowed to request verification.

Rate limiting is process-local and is explicitly an availability control, not a distributed security boundary. HITL requests are in-memory and survive only for the running process; authenticated users may list, approve, and reject them. Role-based approver authorization and durable HITL storage are not implemented.

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
| `HITL_TTL_SECONDS` | In-memory approval request lifetime |
| `VELOCITY_*` | Thresholds for the reusable velocity-tracker component |

Never commit `.env`, private PEM keys, database backups, or audit logs. Use a unique high-entropy `JWT_SECRET_KEY` in every non-development environment.

## Local development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The service initializes local tables on startup. For managed deployments, apply the Alembic migration before application rollout:

```bash
alembic upgrade head
alembic check
alembic current
```

## API

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | No | Liveness |
| GET | `/api/v1/ready` | No | Database and configured-Redis readiness |
| POST | `/api/v1/auth/register` | No | Create a user and access token |
| POST | `/api/v1/auth/login` | No | Obtain an access token |
| GET | `/api/v1/auth/me` | Bearer | Current user |
| POST | `/api/v1/intent/verify` | No | Evaluate an action and issue an execution token when allowed |
| POST | `/api/v1/intent/execute` | No | Consume one execution token |
| GET | `/api/v1/approval/pending` | Bearer | List pending HITL requests |
| POST | `/api/v1/approval/{request_id}/approve` | Bearer | Approve a HITL request |
| POST | `/api/v1/approval/{request_id}/reject` | Bearer | Reject a HITL request |
| GET | `/api/v1/.well-known/jwks.json` | No | Execution-token public key |

OpenAPI is available at `/openapi.json` only when `DEBUG=true`.

## Docker

`docker compose up --build` starts the application, PostgreSQL, and Redis. Compose forces production mode, PostgreSQL, Redis, and a non-empty `JWT_SECRET_KEY`; the application image runs as the non-root `intentlock` user. Persist the PostgreSQL and Redis volumes and forward `logs/audit_trail.jsonl` to centralized storage. The supplied compose credentials are development-only bootstrap values and must be replaced in a real deployment.

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

`--no-cov` prevents pytest-cov’s configured inner collector from conflicting with the outer coverage command.

## Operations

Audit events are written as JSONL to `logs/audit_trail.jsonl` and include timestamps, event type, and correlation ID. Preserve those logs according to the organization’s retention policy, alert on repeated policy/replay failures, rotate JWT and execution-signing material through a controlled deployment, and restore PostgreSQL/Redis from tested backups.

On an incident, restrict API ingress, rotate affected secrets, retain audit logs, investigate correlation IDs, and invalidate/redeploy signing material as appropriate. Tokens are intentionally short lived; replay attempts are denied.

## Future extension points

`KMSKeyManager` is an interface-shaped placeholder, not a configured KMS integration. Provider-backed signing, durable/role-based HITL approvals, distributed rate limiting, and automatic key rotation are future deployment capabilities, not V4 runtime features.

V4.0 has no known release-blocking or reasonably fixable production deficiencies within the defined V4 scope. Future security patches, dependency updates, infrastructure changes, and new capabilities remain normal post-release maintenance.
