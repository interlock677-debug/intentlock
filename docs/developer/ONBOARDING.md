# Developer Onboarding

Use this checklist to get a new developer productive with IntentLock in their first week.

## Day 1: Environment setup

- [ ] Clone the repository
- [ ] Create and activate a virtual environment (Python 3.11+)
- [ ] Install dependencies: `pip install -e ".[dev,security]"`
- [ ] Copy `.env.example` to `.env`
- [ ] Run `uvicorn app.main:app --reload` and confirm `GET /api/v1/health` returns 200
- [ ] Run `pytest -q` and confirm all tests pass

## Day 1: Read

- [ ] `README.md` — project overview, threat model, configuration
- [ ] `docs/architecture/ARCHITECTURE.md` — layers, trust boundaries, request flow
- [ ] `docs/developer/QUICKSTART.md` — first integration with the SDK

## Day 2: Security model

- [ ] `docs/security/SECURITY_ASSURANCE_REPORT.md` — controls, findings, test evidence
- [ ] `docs/security/SECURITY_HARDENING_ROADMAP.md` — P0/P1/P2/P3 roadmap
- [ ] `app/domain/services/tool_security.py` — adversarial argument validation
- [ ] `app/infrastructure/security/ed25519_execution_token_service.py` — token lifecycle
- [ ] `app/infrastructure/logging/audit_logger.py` — JSONL + hash-chain integrity

## Day 2: Hands-on

- [ ] Register a user via `/api/v1/auth/register`
- [ ] Verify an intent via the SDK `verify_intent`
- [ ] Consume the returned execution token via `consume_execution_token`
- [ ] Trigger a blocked action (destructive SQL) and observe `SecurityError`

## Day 3: Policy engine

- [ ] Read `config/policies.yaml`
- [ ] Add a new blocked pattern (e.g., `"DROP TABLE users"`)
- [ ] Run `pytest tests/unit/test_policy_engine.py -q`
- [ ] Run `pytest tests/integration/test_adversarial_security.py -q`

## Day 3: HITL workflow

- [ ] Read `app/domain/services/hitl_queue.py`
- [ ] Create an approval request via the SDK or direct API
- [ ] Approve the request via `approve_request`
- [ ] Verify the audit log captures the decision

## Day 4: SDK internals

- [ ] Read `sdk/intentlock.py` — `IntentLockGuard` and `guard_tool`
- [ ] Read `sdk/langchain_adapter.py` — `IntentLockLangChainTool`
- [ ] Write a small script that wraps a fake tool with `guard_tool`
- [ ] Read `tests/unit/test_sdk_guard.py` and `tests/unit/test_sdk_langchain_adapter.py`

## Day 4: Integrations

- [ ] Read `app/infrastructure/integrations/` — IAM, monitoring, SIEM, ticketing
- [ ] Enable the monitoring adapter in `.env` and confirm metrics endpoint
- [ ] Read `tests/unit/integrations/` for adapter test patterns

## Day 5: CI/CD and operations

- [ ] Review `.github/workflows/ci.yml`, `.github/workflows/security.yml`, `.github/workflows/docker-verify.yml`
- [ ] Run `ruff check app sdk tests` and `mypy app`
- [ ] Run `python -m bandit -r app sdk`
- [ ] Read `docs/operations/PRODUCTION_READINESS_PLAN.md`

## Week 1: Ship something

- [ ] Propose a policy change or bug fix
- [ ] Write a test that reproduces the issue
- [ ] Fix the issue
- [ ] Run the full quality gate locally (`ruff`, `mypy`, `pytest`, `coverage`, `alembic check`)
- [ ] Open a pull request with a clear description

## Useful commands

```bash
# Run tests with coverage
pytest -q

# Lint
ruff check app sdk tests

# Type check
mypy app sdk

# Security scan
python -m bandit -r app sdk

# Dependency audit
pip-audit

# Compile check
python -m compileall app sdk tests

# Database migrations
alembic upgrade head
alembic check
alembic current
```

## Getting help

- GitHub Issues: bug reports and feature requests
- Documentation: `docs/` directory
- SDK reference: `sdk/README.md`
