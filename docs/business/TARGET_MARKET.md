# IntentLock — Target Market

## Primary buyers

### 1. AI-native product teams

Teams building customer-facing or internal AI agents that call databases, APIs, shell commands, or financial tools. They need a control plane that enforces policy without rewriting agent logic.

**Signals:**
- Using LangChain, CrewAI, AutoGen, or custom agent frameworks
- Agents have access to production data or financial systems
- Security or compliance team has flagged "agent permissions" as a risk

### 2. Enterprise platform / security engineering

Teams embedding agentic workflows into internal tools (IT ops, DevOps, customer support). They need SSO, RBAC, SIEM integration, and compliance evidence.

**Signals:**
- Okta, Azure AD, or LDAP for identity
- Splunk, Sentinel, or ELK for log aggregation
- Existing SOC 2 or ISO 27001 program

### 3. Regulated-industry technologists

Financial services, healthcare, and legal teams that must demonstrate audit trails, approval workflows, and evidence of intent before execution.

**Signals:**
- SOC 2, HIPAA, PCI-DSS, or GDPR compliance requirements
- Human-in-the-loop approval for high-risk actions
- Need for tamper-evident logs

## Secondary buyers

- **Cybersecurity teams** evaluating AI agent attack surface
- **DevOps / platform teams** running internal AI assistants with shell or database access
- **Open-source maintainers** building agent frameworks and needing a security layer

## Buyer personas

| Persona | Role | Priority |
|---------|------|----------|
| Security Architect | Designs zero-trust controls for agentic systems | Policy enforcement, audit trails, integration with existing security stack |
| Engineering Lead | Ships agent features fast | SDK quality, documentation, minimal integration effort |
| CISO / CTO | Manages risk and compliance | SLA, pentest reports, compliance evidence, KMS/HSM support |
| DevOps Engineer | Deploys and operates the gateway | Docker, Kubernetes, observability, managed vs. self-hosted |

## Use cases

| Use case | Tier | Description |
|----------|------|-------------|
| Database query guard | Free | Prevent destructive SQL and data exfiltration from agent-driven queries |
| Financial transfer approval | Business | Require HITL for wire transfers, payroll changes, or invoice payments |
| Shell command sandbox | Pro | Restrict agent shell access to approved commands and directories |
| Compliance evidence pack | Business | Export HMAC-signed audit evidence for SOC 2, HIPAA, or internal review |
| Multi-tenant SaaS | Enterprise | Isolate tenants with hierarchical RBAC and per-tenant policy rules |
| Air-gapped deployment | Enterprise | Run IntentLock in a classified or disconnected environment with HSM-backed keys |

## Market trends

- Industry analysts predict significant growth in AI agent adoption for internal-facing applications.
- Prompt injection is now in the OWASP Top 10 for LLM applications.
- Regulators (EU AI Act, NIST AI RMF) increasingly require audit trails and human oversight for high-risk AI systems.

## Positioning statement

For AI-native teams that need to secure agent tool execution, IntentLock is a proof-of-intent gateway that evaluates every action before it runs, issues single-use execution tokens, and produces tamper-evident audit logs. Unlike traditional IAM or WAFs, IntentLock operates at the agent reasoning layer, stopping prompt-injection hijacks and policy violations before they reach production systems.
