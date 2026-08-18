# IntentLock 4.0 Architecture

## Components

IntentLock uses a layered Python design:

```text
FastAPI presentation -> application use cases/ports -> domain services -> infrastructure adapters
```

- `app/presentation`: FastAPI routes, middleware, dependency wiring.
- `app/application`: authentication DTOs, use cases, and port interfaces.
- `app/domain`: entities, value objects, policy, intent evaluation, HITL queue, and velocity tracker.
- `app/infrastructure`: settings, SQLAlchemy, Alembic models, Redis, cryptography, and audit logging.
- `sdk`: standard Python and LangChain callable wrappers.

## Trust boundaries

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Agent     │────▶│  IntentLock  │────▶│   Redis     │
│   / Tool    │     │   Gateway    │     │  (nonce)    │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │  PostgreSQL  │
                    │  (durable)   │
                    └──────────────┘
```

| Boundary | Description | Enforcement |
|----------|-------------|-------------|
| Agent → Gateway | `/intent/verify` and `/intent/execute` are unauthenticated | Network controls (firewall, service mesh, API gateway) |
| User → Gateway | `/auth/*` and `/approval/*` require bearer tokens | HS256 JWT validation |
| Gateway → Redis | Atomic nonce consumption for replay protection | Redis AUTH + fail-closed in production |
| Gateway → Database | User data, approvals, audit events, token records | SQLAlchemy ORM, connection pooling |
| Gateway → External | SDK invokes wrapped local tools after token consumption | SDK enforces single-use semantics |

## Request flow

```text
Agent/tool -> SDK -> POST /intent/verify -> evaluator + policy -> Ed25519 execution token
        -> POST /intent/execute -> nonce store -> SDK invokes wrapped local tool
```

The SDK validates its configured gateway URL as HTTP(S). The API validates request DTOs and intent models. `/intent/verify` returns 403 for blocked actions; permitted actions receive an execution JWT containing `sub`, `tool`, `iat`, `nbf`, `exp`, `jti`, and `type=execution`. `/intent/execute` verifies the Ed25519 signature and claims, applies strict expiry, atomically consumes `jti`, and rejects replay.

Access tokens are separate HS256 bearer JWTs issued by authentication use cases. They require `sub`, `email`, `exp`, `iat`, and `jti`, validate `nbf`, and require `type=access`. They protect `/auth/me` and all HITL routes.

Intent verification and execution endpoints are not bearer-authenticated in this implementation; deployment must limit their network access to authorized agents. The execution endpoint acknowledges verified token consumption; it does not execute an external business action itself.

## Security controls

- Intent evaluator: regex and `sqlglot` destructive-SQL checks, policy evaluation, transfer limits, and payload detection.
- Policy engine: YAML-configured block patterns and deterministic risk scoring from `config/policies.yaml`.
- Replay protection: `CompositeNonceStore` combines memory L1 with Redis L2. Production requires Redis configuration and Redis failure makes consumption fail closed.
- Middleware: correlation ID propagation, baseline response headers, CORS, process-local sliding-window request limits, and configurable request size limits.
- Logging: JSONL verification and security events with correlation IDs; tool arguments and execution tokens are not added to audit records.
- Persistence: SQLAlchemy models for users, execution-token records, audit events, and approval requests. Approval requests are durably persisted in PostgreSQL.

## Attack paths and mitigations

| Attack Path | Mitigation |
|-------------|-----------|
| Replay execution token | Atomic nonce consumption in Redis; fail-closed on Redis failure |
| Forge access token | HS256 with short expiration; requires JWT_SECRET_KEY |
| Bypass policy via casing/whitespace | Regex with word boundaries and flexible whitespace |
| Path traversal to key files | `..` component rejection in key directory validation |
| X-Forwarded-For spoofing | Trusted proxy list validation; rightmost untrusted IP extraction |
| Large request body DoS | RequestSizeLimitMiddleware (default 1 MiB) |
| Redis unauthorized access | `--requirepass` in Compose; authentication in health checks |
| PostgreSQL unauthorized access | Strong credentials via environment variables |

## Failure behavior

Invalid tokens, expired tokens, replayed tokens, unavailable Redis during production nonce consumption, and blocked policy results deny the requested operation. Database readiness reports `not_ready` on database failure. If Redis is configured and unavailable, readiness also reports `not_ready`.

Rate limiting and HITL use in-process state for rate limiting. Their process restart behavior is therefore explicit: rate-limit counters are lost. HITL requests are durably persisted in PostgreSQL and survive application restarts.

If Redis is down in production, execution token consumption fails closed (denied). Intent verification and evaluation continue to operate, but no execution tokens can be consumed.

## Deployment

The Docker image is a multi-stage Python 3.11 build and runs as a non-root `intentlock` user. Compose connects it to PostgreSQL 16 and Redis 7 with health checks, persistent data volumes, and production environment settings. Apply migrations before rollout and use deployment-managed secrets rather than the compose example credentials.

### Docker image hardening

- Base image: `python:3.11-slim-bookworm`
- Multi-stage build to reduce final image size
- Non-root `intentlock` user
- `/tmp` mounted as tmpfs with `noexec,nosuid` restrictions
- `no-new-privileges` security option
- Image metadata labels
- Build-time secret exposure verification
- Minimal package footprint

## Key management

`EnvKeyManager` provides the active execution signing key and can load/persist an Ed25519 private key from `EXECUTION_KEY_PATH`. Without that path, the execution key exists only for the running process. `KMSKeyManager` defines an extension contract but is not an active provider integration; no automatic KMS/HSM rotation exists in V4.

## Operational checklist

1. Set production PostgreSQL, Redis, CORS origins, and a high-entropy JWT secret.
2. Provide and protect stable execution-signing material if token verification must survive a restart or span instances.
3. Run `alembic upgrade head`, then confirm `alembic check` and `alembic current`.
4. Restrict intent API ingress to trusted agents, terminate TLS upstream, and collect JSONL audit logs.
5. Back up PostgreSQL and Redis, test restore procedures, and keep an incident playbook for credential rotation and correlation-ID investigation.
6. Run compilation, Ruff, MyPy, pytest, coverage, Alembic, and application-import checks before release.
7. Run CI/CD pipelines with security scanning (pip-audit, Bandit, Semgrep) and SBOM generation.
8. Verify Docker image scanning results and address HIGH/CRITICAL vulnerabilities.

## Extension boundaries

Role-based approval authorization and database-backed durable HITL storage are implemented in V4. Distributed rate limiting, active KMS/HSM integration, downstream-resource authorization, and automatic key rotation are not implemented by V4. They require deliberate architecture and deployment work rather than configuration-only claims.

## Security boundary review

| Boundary | In Scope | Out of Scope |
|----------|----------|--------------|
| Agent → Gateway | Network access control, TLS termination | SDK-level authorization |
| User → Gateway | JWT validation, bearer token enforcement | Identity provider integration |
| Gateway → Redis | Authentication, fail-closed behavior | Redis cluster security |
| Gateway → Database | Connection security, ORM injection prevention | Database-level access control |
| Gateway → External | SDK enforces single-use before tool invocation | Tool-level authorization |
