# Competitive Comparison

How IntentLock compares to alternative approaches for securing AI agent tool execution.

> **Note:** Competitor feature claims are based on publicly available product documentation and may not reflect current capabilities. Verify with each vendor before procurement decisions.

## Comparison matrix

| Dimension | IntentLock | Custom middleware | LangChain / framework guardrails | Commercial API security gateway |
|-----------|-----------|-------------------|----------------------------------|---------------------------------|
| **Scope** | Agent intent layer | Application layer | Framework-specific | Network / API layer |
| **Token model** | Ed25519 execution tokens, single-use, atomic replay protection | None or custom | None or framework-specific | API keys, mTLS, OAuth |
| **Policy engine** | YAML, versioned, precedence, rollback | Ad-hoc in code | Limited or none | Rule-based WAF policies |
| **Adversarial tests** | 88 tests (SQLi, SSRF, path traversal, prompt injection, replay) | Depends on team | Minimal | Depends on vendor |
| **HITL approval** | Database-backed, RBAC, durable | Custom build | None | None |
| **Audit log** | JSONL + SHA-256 hash-chain + HMAC compliance export | Custom | None | Standard access logs |
| **SDK** | Python + LangChain wrapper | None | Built-in | None |
| **Integration effort** | Decorator + REST client | High | Low (but limited scope) | Medium (proxy / sidecar) |
| **Compliance evidence** | HMAC-signed packages | Custom | None | Partial (log export) |
| **Multi-tenant** | Identity-based tenant isolation | Custom | None | Partial |
| **SSRF protection** | URL scheme, private IP, DNS resolution checks | Custom | Rare | Partial |
| **SQL injection** | sqlglot parser + regex | Custom | Rare | Partial |
| **Prompt injection** | 10 regex patterns + reasoning-step scan | None | Rare | None |
| **Key management** | Ed25519 with rotation + KMS/HSM placeholder | Custom | None | Vendor-managed |
| **Replay protection** | Atomic Redis nonce store, fail-closed | Custom | None | Rate limit only |
| **Rate limiting** | Proxy-aware, Redis-backed, in-memory fallback | Custom | None | Standard rate limit |
| **Observability** | Correlation IDs, metrics endpoint | Custom | Built-in | Vendor dashboards |
| **CI/CD security** | pip-audit, Bandit, Safety, SBOM, Docker scan | Depends | Depends | Vendor-managed |
| **License** | Proprietary (Free / Pro / Business / Enterprise) | Varies | Open source | Proprietary |
| **Pricing** | $0 – custom | Engineering cost | Free / open source | Varies by vendor |

## When to choose IntentLock

- You are building or operating **AI agents** that call tools (databases, APIs, shell, financial systems)
- You need a **control plane between intent and execution**, not just network-level security
- You want **policy-as-code** with versioning, rollback, and testability
- You require **tamper-evident audit logs** for compliance (SOC 2, HIPAA, PCI-DSS, GDPR)
- You need **human-in-the-loop approvals** for high-risk operations
- You want a **Python SDK and LangChain integration** that does not require rewriting your agent

## When another approach may be sufficient

- Your agents only call **read-only public APIs** with no sensitive data
- You have **no compliance or audit requirements**
- You are building a **proof of concept** with no production data
- You already have a **mature API gateway** with fine-grained OAuth scopes and are willing to build agent-specific guardrails in application code

## Feature deep-dive

### Execution tokens vs. API keys

IntentLock issues ephemeral Ed25519 execution tokens that are valid for 1–60 seconds and consumed exactly once. API keys and OAuth tokens are long-lived and reusable; they protect access but do not prevent a compromised agent from replaying a valid request.

### Policy engine vs. WAF rules

IntentLock policies are evaluated against the agent's reasoning step, tool name, and tool arguments. WAF rules inspect HTTP headers and payloads. IntentLock can block a `DROP TABLE` in a tool argument before the database driver ever sees it.

### Audit log vs. access log

IntentLock writes structured JSONL events with correlation IDs, tool arguments (redacted), and a SHA-256 hash chain. Standard access logs capture request metadata but not the intent evaluation outcome, policy version, or approval chain.

### SDK vs. DIY glue

The IntentLock SDK provides `verify_intent`, `consume_execution_token`, `guard_tool`, and LangChain wrappers with retry logic, URL validation, and consistent error handling. Building and maintaining equivalent glue code across teams is a hidden cost.

---

*This comparison is based on publicly available information and product documentation as of 2026-08-18. Feature availability varies by vendor and plan.*
