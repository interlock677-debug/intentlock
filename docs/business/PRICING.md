# IntentLock — Pricing & Plans

## Overview

IntentLock is offered in four tiers. All tiers include the core proof-of-intent gateway, Python SDK, and security updates. Higher tiers add usage limits, support, enterprise integrations, and deployment options.

---

## Free

**Price:** $0 / month  
**Billing:** No credit card required

| Feature | Limit |
|---------|-------|
| Agents | 1 |
| Intents / day | 100 |
| HITL approvers | 1 |
| Policy rules | 10 |
| Support | Community (GitHub Issues) |
| Deployment | Local / Docker Compose |
| Audit retention | 7 days |
| SLA | None |

**Who it is for:**  
Individual developers, proof-of-concept projects, open-source contributors, and students evaluating IntentLock.

**How to start:**  
`pip install intentlock` or clone the repository and run `uvicorn app.main:app --reload`.

---

## Pro

**Price:** $49 / seat / month (minimum 3 seats)  
**Billing:** Monthly or annual (2 months free with annual)

| Feature | Limit |
|---------|-------|
| Agents | 10 |
| Intents / day | 10,000 |
| HITL approvers | 5 |
| Policy rules | 100 |
| Support | Priority email / chat (24h response) |
| Deployment | Single-region cloud, Docker, Kubernetes |
| Audit retention | 30 days |
| SLA | 99.9% uptime |
| Integrations | IAM, monitoring, SIEM adapter port (Splunk, Sentinel, QRadar mock adapters), ticketing adapter port (Jira, ServiceNow mock adapters) |
| SSO | SAML 2.0 and OIDC adapter interfaces (mock implementations; production protocols require integration) |

**Who it is for:**  
Startups and small teams shipping agentic features to production. Teams that need SSO, higher rate limits, and faster support than community tier.

**How to upgrade:**  
Contact sales or subscribe through the developer portal. A license key is injected via `INTENTLOCK_LICENSE_KEY`.

---

## Business

**Price:** $199 / seat / month (minimum 5 seats)  
**Billing:** Monthly or annual

| Feature | Limit |
|---------|-------|
| Agents | 100 |
| Intents / day | 100,000 |
| HITL approvers | 25 |
| Policy rules | 1,000 |
| Support | Priority email / chat (8h response) + named CSM |
| Deployment | Multi-region, Kubernetes, Terraform modules |
| Audit retention | 90 days |
| SLA | 99.95% uptime |
| Integrations | IAM, monitoring, SIEM (Splunk, Sentinel, ELK), ticketing (Jira, ServiceNow) |
| SSO | SAML 2.0 and OIDC adapter interfaces (mock implementations; production protocols require integration) |
| Compliance exports | HMAC-signed evidence packages |
| Tenant isolation | Multi-tenant with RBAC |

**Who it is for:**  
Mid-market companies and regulated teams (fintech, healthtech, legaltech) that require compliance evidence, SIEM integration, and multi-tenant isolation.

**How to upgrade:**  
Contact sales for a Business trial. Trials include a dedicated environment and onboarding call.

---

## Enterprise

**Price:** Custom (starts at $10,000 / month)  
**Billing:** Annual contract

| Feature | Limit |
|---------|-------|
| Agents | Unlimited |
| Intents / day | Unlimited |
| HITL approvers | Unlimited |
| Policy rules | Unlimited |
| Support | 24x7 phone / email / Slack + named TAM |
| Deployment | Dedicated cloud, VPC, on-prem, air-gapped |
| Audit retention | 1 year (configurable) |
| SLA | 99.99% uptime |
| Integrations | Full adapter catalog + custom adapters |
| SSO | SAML 2.0, OIDC, LDAP, PIV/CAC |
| Compliance exports | Custom schemas, HMAC, retention policies |
| Tenant isolation | Hierarchical orgs, identity-based ACL |
| Key management | KMS/HSM key management interface (placeholder for external KMS/HSM integration) |
| Security | Secret scanning, dependency auditing, image scanning in CI/CD |
| Training | On-site training, architecture review |

**Who it is for:**  
Large enterprises, government, and regulated industries requiring dedicated infrastructure, custom SLAs, and professional services.

**How to buy:**  
Contact enterprise sales. Typical engagement: 2-week proof of concept, followed by architecture review and SOW.

---

## Feature matrix

| Feature | Free | Pro | Business | Enterprise |
|---------|------|-----|----------|------------|
| Proof-of-intent gateway | Yes | Yes | Yes | Yes |
| Python SDK | Yes | Yes | Yes | Yes |
| LangChain wrapper | Yes | Yes | Yes | Yes |
| Policy engine (YAML) | Yes | Yes | Yes | Yes |
| HITL approval queue | Yes | Yes | Yes | Yes |
| Ed25519 execution tokens | Yes | Yes | Yes | Yes |
| Redis replay protection | Self-hosted | Self-hosted / managed | Managed | Managed / on-prem |
| Audit log (JSONL + hash-chain) | Yes | Yes | Yes | Yes |
| Adversarial test suite | Open source | Included | Included | Included |
| Rate limiting | Local | Distributed | Distributed | Distributed |
| RBAC | No | Basic | Advanced | Hierarchical identity-based authorization |
| Multi-tenant isolation | No | No | Tenant isolation in database and authorization | Tenant isolation + per-tenant policy rules |
| Compliance evidence export | No | No | Yes | Yes |
| SIEM integration | No | No | SIEM adapter port (Splunk, Sentinel, QRadar mock adapters) | SIEM adapter port + custom adapters |
| Ticketing integration | No | No | Ticketing adapter port (Jira, ServiceNow mock adapters) | Ticketing adapter port + custom adapters |
| SSO | SAML 2.0 and OIDC adapter interfaces (mock implementations) | SAML 2.0 and OIDC adapter interfaces (mock implementations) | SAML 2.0 and OIDC adapter interfaces (mock implementations) | SAML 2.0, OIDC, LDAP, PIV/CAC adapter interfaces (mock implementations) |
| KMS/HSM | No | No | No | KMS/HSM key management interface (placeholder) |
| SLA | None | 99.9% | 99.95% | 99.99% |
| Support | Community | Priority (24h) | Priority (8h) + CSM | 24x7 + TAM |
| Pentest | No | No | On request | On request |
| Training | Docs | Docs | Webinar | On-site + custom |

---

## Frequently asked questions

**Can I self-host Free tier?**  
Yes. Free tier is open source and can be deployed on your own infrastructure.

**Do intent limits reset daily?**  
Yes. Limits reset at midnight UTC.

**What happens when I exceed a limit?**  
The gateway returns `429 Too Many Requests` for intent verification. Execution tokens are not issued until the next window.

**Is there a trial for Business or Enterprise?**  
Yes. Business trials are 14 days. Enterprise engagements begin with a 2-week proof of concept.

**Do you offer discounts for nonprofits or education?**  
Yes. Contact sales for nonprofit and academic pricing.

**How do I cancel?**  
Cancel from the developer portal at any time. Annual contracts may be subject to a 30-day notice period.
