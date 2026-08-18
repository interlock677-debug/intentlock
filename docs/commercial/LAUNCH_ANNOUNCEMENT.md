# Launch Announcement — IntentLock 4.0

**FOR IMMEDIATE RELEASE**  
**Date:** 2026-08-18  
**Contact:** sales@intentlock.io

---

## IntentLock launches a proof-of-intent authorization gateway for AI agents

IntentLock 4.0 gives engineering and security teams a control plane that evaluates every agent tool call before it executes, issues short-lived single-use tokens, and produces tamper-evident audit logs.

As AI agents gain access to databases, financial systems, and internal APIs, the attack surface shifts from the perimeter to agent reasoning. Prompt injection, tool misuse, and unauthorized data access are now top concerns for teams shipping agentic features. IntentLock operates at the intent layer, not the network layer, stopping malicious or accidental tool execution before it reaches production systems.

## What makes IntentLock different

Traditional IAM secures user identities. Web application firewalls inspect network traffic. Neither inspects the reasoning step that triggers a tool call. IntentLock fills that gap with:

- **Proof-of-intent evaluation** — regex, sqlglot parser, URL/scheme/path validation, and policy-as-code
- **Short-lived execution tokens** — Ed25519-signed JWTs consumed exactly once with atomic nonce replay protection
- **Policy engine with rollback** — YAML-configured, versioned rules with precedence and rollback
- **Human-in-the-loop queue** — database-backed durable approvals with RBAC
- **Tamper-evident audit log** — JSONL events chained with SHA-256 hashes and HMAC-signed compliance exports
- **Python SDK + LangChain wrapper** — drop-in integration with `guard_tool` decorator

## Proven at scale (for a gateway)

- 760 automated tests with 99.92% statement coverage
- Adversarial security tests covering JWT forgery, replay, SQL injection, SSRF, path traversal, and prompt injection
- CI/CD with Bandit, Safety, SBOM generation, and Docker image scanning
- Production-ready Docker image: multi-stage, non-root user, tmpfs, `no-new-privileges`

## Pricing and availability

IntentLock 4.0 is available today in four tiers:

| Tier | Price | Audience |
|------|-------|----------|
| Free | $0 | Developers, PoC, OSS |
| Pro | $49/seat/mo | Startups, small teams |
| Business | $199/seat/mo | Mid-market, regulated |
| Enterprise | Custom | Large orgs, regulated |

All tiers include the core gateway, Python SDK, and security updates. Business and Enterprise tiers add SSO, SIEM integration, compliance evidence exports, and KMS/HSM support.

**Free tier is open source and available now on GitHub.**

## Quote

> "Agents are only as secure as the control plane that governs their actions. IntentLock is the missing piece that lets teams ship agentic features without accepting unlimited trust in the agent's reasoning."
>
> — *Product announcement*

## Get started

- **Docs:** `docs/developer/QUICKSTART.md`
- **SDK:** `pip install intentlock`
- **GitHub:** `https://github.com/interlock677-debug/intentlock`
- **Pricing:** `docs/business/PRICING.md`

## About IntentLock

IntentLock is a proof-of-intent authorization gateway for AI agents. It evaluates proposed tool actions, issues single-use execution tokens, and produces tamper-evident audit logs. For more information, visit `https://intentlock.io`.

---

*This release includes Free, Pro, Business, and Enterprise tier documentation. License keys, managed cloud, and enterprise support are available by contacting sales@intentlock.io.*
