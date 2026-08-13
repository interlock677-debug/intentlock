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

## Request flow and trust boundaries

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
- Middleware: correlation ID propagation, baseline response headers, CORS, and process-local sliding-window request limits.
- Logging: JSONL verification and security events with correlation IDs; tool arguments and execution tokens are not added to audit records.
- Persistence: SQLAlchemy models for users, execution-token records, audit events, and approval requests. Only user persistence is currently used by HTTP routes; Alembic migration `0001_initial_schema` creates all four tables.

## Failure behavior

Invalid tokens, expired tokens, replayed tokens, unavailable Redis during production nonce consumption, and blocked policy results deny the requested operation. Database readiness reports `not_ready` on database failure. If Redis is configured and unavailable, readiness also reports `not_ready`.

Rate limiting and HITL use in-process state. Their process restart behavior is therefore explicit: rate-limit counters and pending approvals are lost. Redis support inside `HITLQueue` is best-effort and is not wired into the route singleton, so it must not be treated as durable approval storage.

## Deployment

The Docker image is a multi-stage Python 3.11 build and runs as a non-root `intentlock` user. Compose connects it to PostgreSQL 16 and Redis 7 with health checks, persistent data volumes, and production environment settings. Apply migrations before rollout and use deployment-managed secrets rather than the compose example credentials.

## Key management

`EnvKeyManager` provides the active execution signing key and can load/persist an Ed25519 private key from `EXECUTION_KEY_PATH`. Without that path, the execution key exists only for the running process. `KMSKeyManager` defines an extension contract but is not an active provider integration; no automatic KMS/HSM rotation exists in V4.

## Operational checklist

1. Set production PostgreSQL, Redis, CORS origins, and a high-entropy JWT secret.
2. Provide and protect stable execution-signing material if token verification must survive a restart or span instances.
3. Run `alembic upgrade head`, then confirm `alembic check` and `alembic current`.
4. Restrict intent API ingress to trusted agents, terminate TLS upstream, and collect JSONL audit logs.
5. Back up PostgreSQL and Redis, test restore procedures, and keep an incident playbook for credential rotation and correlation-ID investigation.
6. Run compilation, Ruff, MyPy, pytest, coverage, Alembic, and application-import checks before release.

## Extension boundaries

Role-based approval authorization, durable HITL workflows, distributed rate limiting, active KMS/HSM integration, downstream-resource authorization, and automatic key rotation are not implemented by V4. They require deliberate architecture and deployment work rather than configuration-only claims.
