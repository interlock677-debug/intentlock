# IntentLock — Product Positioning

## Elevator pitch

IntentLock is the proof-of-intent authorization layer for AI agents. Before an agent calls a tool, IntentLock evaluates the proposed action, issues a short-lived Ed25519 execution token when the action is permitted, and consumes that token exactly once. This stops prompt-injection hijacks, unauthorized data access, destructive operations, and compliance violations before they happen.

## Problem we solve

AI agents execute tools on behalf of users. Without a control plane between intent and execution, an agent can be tricked into:

- Running destructive SQL or shell commands
- Exfiltrating sensitive data
- Initiating unauthorized financial transfers
- Violating regulatory compliance rules

Traditional IAM secures users; it does not secure agent reasoning steps. IntentLock fills that gap.

## Core value proposition

| Claim | Evidence |
|-------|----------|
| Zero-trust tool execution | Ed25519 execution tokens with atomic nonce consumption and strict expiry |
| Policy-as-code | YAML-configured rules with versioning, precedence, and rollback |
| Adversarial hardening | 88 adversarial security tests; regex + sqlglot parser + URL/scheme/path validation |
| Production-ready | 760 tests, 99.92% statement coverage, HS256 JWT, Redis fail-closed, JSONL audit + hash-chain |
| Developer-friendly | Python SDK, `guard_tool` decorator, LangChain wrapper, 5-minute quickstart |
| Compliance-ready | RBAC HITL queue, tamper-evident compliance evidence export, SBOM, dependency scanning in CI |

## Target market

- **AI-native companies** building agents that call databases, APIs, shell commands, or financial tools
- **Enterprise platform teams** embedding agentic workflows into internal tools
- **Regulated industries** (financial services, healthcare, legal) requiring audit trails and approval gates
- **Security teams** needing defense-in-depth against prompt injection and tool misuse

## Competitive differentiation

| Dimension | IntentLock | Traditional IAM | Web Application Firewalls |
|-----------|-----------|-----------------|---------------------------|
| Secures agent reasoning | Yes | No | No |
| Short-lived execution tokens | Yes (Ed25519, single-use) | No | No |
| Policy engine with rollback | Yes | No | Partial |
| Adversarial test suite | 88 tests | N/A | Partial |
| Python SDK + LangChain | Native | Requires custom glue | No |
| HITL with RBAC | Database-backed | No | No |
| Hash-chain audit log | Yes | Rare | No |

## Pricing tiers

See `PRICING.md` for detailed plans.

| Tier | Price | Audience | Key limits |
|------|-------|----------|------------|
| Free | $0 | Developers, PoC, OSS | 1 agent, 100 intents/day, community support |
| Pro | $49/seat/mo | Startups, small teams | 10 agents, 10k intents/day, priority support, SSO |
| Business | $199/seat/mo | Mid-market, regulated | 100 agents, 100k intents/day, RBAC, audit exports, SIEM |
| Enterprise | Custom | Large orgs, regulated | Unlimited, dedicated infra, KMS/HSM interface, SLA, pentest on request, custom policy rules |

## Go-to-market themes

1. **Secure by default** — The gateway is the control plane agents cannot bypass.
2. **Policy as code** — Versioned, testable, rollback-capable rules in YAML.
3. **Compliance out of the box** — HMAC-signed evidence, hash-chain logs, RBAC approvals.
4. **Developer velocity** — Drop-in SDK and decorator; no agent rewrite required.
