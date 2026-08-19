# IntentLock

**Proof-of-intent authorization control plane for AI agents.**

IntentLock evaluates a proposed tool action before it executes, returns a short-lived Ed25519 execution token for permitted actions, and consumes that token exactly once. This stops prompt-injection hijacks, unauthorized data access, destructive operations, and compliance violations before they reach production systems.

> **Tiers:** Free | Pro ($49/seat/mo) | Business ($199/seat/mo) | Enterprise (custom)  
> See [`docs/business/PRICING.md`](docs/business/PRICING.md) for details.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green)
![License](https://img.shields.io/badge/license-Proprietary-lightgrey)
![Tests](https://img.shields.io/badge/tests-760%20passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-99.92%25-ff69b4)

---

## Core message

**Before an AI agent executes a high-impact tool action, IntentLock evaluates whether that action should be allowed.**

```
AI Agent
   ↓
"Transfer $50,000"
   ↓
INTENTLOCK
   ↓
Policy + Authorization + Risk
   ↓
ALLOW / DENY / HUMAN APPROVAL
   ↓
Execution + Audit Trail
```

---

## The problem

AI agents execute tools on behalf of users. Without a control plane between intent and execution, an agent can be tricked into:

- Running destructive SQL or shell commands
- Exfiltrating sensitive data
- Initiating unauthorized financial transfers
- Violating regulatory compliance rules

Traditional IAM secures users; it does not secure agent reasoning steps. IntentLock fills that gap.

---

## Demo

Run the included demonstration to see IntentLock in action:

```bash
python examples/demo_agent_defense.py
```

The demo shows three scenarios:

1. **Legitimate request** — a safe SQL query is permitted
2. **Prompt injection attack** — a `DROP TABLE` command is blocked
3. **Unauthorized transfer** — a transfer exceeding the user's stated limit is blocked

Output includes audit trail verification from `logs/audit_trail.jsonl`.

---

## Architecture

```text
AI Agent / Tool
      ↓
IntentLock Gateway
      ↓
Policy Evaluation
      ↓
Authorization
      ↓
Tool Security
      ↓
Human Approval (optional)
      ↓
Execution
      ↓
Audit Trail
```

The gateway sits between the agent and the tools it calls. Every tool action is evaluated for intent, policy compliance, and security risk before an Ed25519 execution token is issued.

---

## Why IntentLock?

| Concern | How IntentLock addresses it |
|---------|----------------------------|
| Prompt injection hijacks | Proof-of-intent evaluation with regex, SQL parsing, URL/scheme/path validation, and policy-as-code |
| Unauthorized tool execution | Short-lived Ed25519 execution tokens consumed exactly once with atomic nonce replay protection |
| Destructive operations | YAML-configured, versioned policy rules with precedence and rollback |
| Compliance violations | Tamper-evident JSONL audit log with SHA-256 hash chains and HMAC-signed exports |
| Lack of visibility | Human-in-the-loop queue with database-backed durable approvals and RBAC |
| Integration friction | Python SDK + LangChain wrapper with `guard_tool` decorator |

---

## Key capabilities

- **Proof-of-intent evaluation** — regex, sqlglot parser, URL/scheme/path validation, and policy-as-code
- **Short-lived execution tokens** — Ed25519-signed JWTs consumed exactly once with atomic nonce replay protection
- **Policy engine with rollback** — YAML-configured, versioned rules with precedence and rollback
- **Human-in-the-loop queue** — database-backed durable approvals with RBAC
- **Tamper-evident audit log** — JSONL events chained with SHA-256 hashes and HMAC-signed compliance exports
- **Python SDK + LangChain wrapper** — drop-in integration with `guard_tool` decorator

---

## Quickstart

```bash
# 1. Clone and enter the repository
git clone https://github.com/interlock677-debug/intentlock.git
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

## Installation

```bash
pip install intentlock
```

---

## Example usage

### Authentication

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

### Authorization

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

### Policy example

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

### HITL workflow

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

---

## Security evidence

This section presents automated repository/testing evidence. It does not claim certification or compliance.

| Check | Result |
|-------|--------|
| Automated tests | 760 passed, 5 skipped, 0 failed |
| Statement coverage | 99.92% |
| Branch coverage | 99.59% |
| Static analysis (Ruff) | 0 errors |
| Type checking (MyPy) | 0 issues |
| Security scanner (Bandit) | 0 High/Medium issues |
| Dependency audit (pip-audit) | 0 known vulnerabilities |
| Adversarial tests | 88 passed |
| SBOM | Generated (156 components) |

### What the evidence shows

- **Automated security testing** — adversarial tests cover JWT forgery, replay attacks, SQL injection, SSRF, path traversal, and prompt injection
- **Dependency auditing** — pip-audit runs in CI; SBOM is generated for supply-chain transparency
- **Static analysis** — Ruff, MyPy, Bandit, and Semgrep are configured in CI
- **Threat model** — documented in [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) and [`docs/security/SECURITY_ASSURANCE_REPORT.md`](docs/security/SECURITY_ASSURANCE_REPORT.md)
- **Security documentation** — assurance report, hardening roadmap, and independent audit are in [`docs/security/`](docs/security/)

### What is not claimed

- This is **not** independent penetration testing by a qualified security firm
- This is **not** a SOC 2, HIPAA, PCI-DSS, or any regulatory compliance certification
- This is **not** a guarantee of security outcomes
- Testing evidence does not equal certification

---

## Security assumptions and boundaries

### Security assumptions

- The intent verification and execution endpoints (`/intent/verify`, `/intent/execute`) require bearer-token authentication (`CurrentUser`). The SDK must provide a valid `auth_token`.
- Access tokens rely on HS256 signature validation and short expiration. They have no server-side replay protection. Rotation and high-entropy secrets are required in non-development environments.
- Execution tokens use Ed25519 signatures with atomic nonce consumption. Redis failure in production causes token consumption to fail closed.
- Rate limiting is process-local when Redis is unavailable. It is an availability control, not a distributed security boundary.
- The SDK validates gateway URLs as HTTP(S) but does not validate TLS certificates or perform network-level access control.

### Security boundaries

- **Bearer-authenticated intent endpoints**: `/intent/verify` and `/intent/execute` require a valid bearer token (`CurrentUser`). The SDK must provide an `auth_token`.
- **Short-lived tokens**: Execution tokens expire in 1–60 seconds. Replay is prevented by atomic nonce consumption.
- **Redis fail-closed**: Production deployments require Redis. If Redis is unavailable, nonce consumption fails and the request is denied.
- **Process-local rate limiting**: When Redis is unavailable, rate limiting falls back to in-memory counters that are not shared across instances.
- **HITL durability**: Approval requests are persisted in PostgreSQL and survive restarts.
- **Key management**: Ed25519 keys are generated in-process by default. Use `EXECUTION_KEY_PATH` to persist keys across restarts. Integrate with a KMS/HSM for production.

---

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

---

## Documentation

- [Developer Quickstart](docs/developer/QUICKSTART.md) — 5-minute setup guide
- [Developer Examples](docs/developer/EXAMPLES.md) — multi-agent, LangChain, HITL, Docker, K8s
- [Developer Onboarding](docs/developer/ONBOARDING.md) — week-one checklist for new engineers
- [SDK Reference](sdk/README.md) — Python SDK and LangChain wrapper docs
- [Architecture](docs/architecture/ARCHITECTURE.md) — layers, trust boundaries, request flow, attack paths
- [Security Assurance Report](docs/security/SECURITY_ASSURANCE_REPORT.md) — controls, test evidence, findings, remediation
- [Security Hardening Roadmap](docs/security/SECURITY_HARDENING_ROADMAP.md) — P0/P1/P2/P3 security roadmap
- [Final Independent Audit](docs/security/FINAL_INDEPENDENT_AUDIT.md) — adversarial test results and evidence
- [Product Positioning](docs/business/PRODUCT_POSITIONING.md) — value proposition, target market, competitive differentiation
- [Pricing](docs/business/PRICING.md) — Free / Pro / Business / Enterprise tier details
- [Target Market](docs/business/TARGET_MARKET.md) — buyer personas, use cases, market trends
- [Enterprise Deployment](docs/commercial/ENTERPRISE_DEPLOYMENT.md) — multi-tenant, multi-region, air-gapped, K8s, DR, compliance

---

## Docker

`docker compose up --build` starts the application, PostgreSQL, and Redis. Compose requires explicitly set credentials via environment variables; the application image runs as the non-root `intentlock` user with a restricted `/tmp` tmpfs mount. Persist the PostgreSQL and Redis volumes and forward `logs/audit_trail.jsonl` to centralized storage.

Example `.env` for Docker Compose:

```bash
POSTGRES_USER=intentlock
POSTGRES_PASSWORD=<secure-random-value>
REDIS_PASSWORD=<secure-random-value>
JWT_SECRET_KEY=<secure-random-value-at-least-32-chars>
```

---

## Project status

IntentLock V4 is an actively developed security and authorization platform for AI-agent workloads. The codebase is functionally complete, tested, and hardened with documented architectural limitations.

### Current state

- **Version:** 4.0.0
- **Python:** 3.11+
- **Framework:** FastAPI 0.115+
- **Tests:** 760 passing with 99.92% statement coverage
- **Database:** SQLite (development), PostgreSQL (production)
- **Cache:** Redis for distributed replay protection and rate limiting

### Known limitations

- Access tokens are stateless JWTs with no server-side replay protection (execution tokens have nonce-based replay protection)
- KMS/HSM integration is defined as an interface placeholder; production deployments must integrate external key management
- Docker image hardening is configured but runtime verification is pending CI execution
- No independent security certification has been obtained
- No regulatory compliance assessment has been performed
- Git-tracked runtime data (`intentlock.db`, `logs/audit_trail.jsonl`) is documented for future history cleanup

---

## Operations

Audit events are written as JSONL to `logs/audit_trail.jsonl` and include timestamps, event type, and correlation ID. Preserve those logs according to the organization's retention policy, alert on repeated policy/replay failures, rotate JWT and execution-signing material through a controlled deployment, and restore PostgreSQL/Redis from tested backups.

On an incident, restrict API ingress, rotate affected secrets, retain audit logs, investigate correlation IDs, and invalidate/redeploy signing material as appropriate. Tokens are intentionally short lived; replay attempts are denied.

---

## Future extension points

`KMSKeyManager` is an interface-shaped placeholder, not a configured KMS integration. Provider-backed signing, automatic key rotation, distributed rate limiting, and downstream-resource authorization are future deployment capabilities, not V4 runtime features.

V4.0 has known limitations documented in `docs/security/SECURITY_ASSURANCE_REPORT.md`. Future security patches, dependency updates, infrastructure changes, and new capabilities remain normal post-release maintenance.

---

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

---

## Commercial

IntentLock is available in Free, Pro, Business, and Enterprise tiers.

- **Free** — Open source, 1 agent, 100 intents/day, community support
- **Pro** — $49/seat/mo, 10 agents, 10k intents/day, SSO, priority support
- **Business** — $199/seat/mo, 100 agents, 100k intents/day, identity-based RBAC, SIEM/ticketing adapter ports, compliance exports
- **Enterprise** — Custom pricing, unlimited agents, KMS/HSM interface, 99.99% SLA, dedicated support

See [`docs/business/PRICING.md`](docs/business/PRICING.md) for full feature comparisons and [`docs/commercial/ENTERPRISE_DEPLOYMENT.md`](docs/commercial/ENTERPRISE_DEPLOYMENT.md) for production patterns.

For sales, partnerships, or enterprise inquiries: **interlock677@gmail.com**
