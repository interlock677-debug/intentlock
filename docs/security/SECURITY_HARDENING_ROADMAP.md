# Security Hardening Roadmap

**Date:** 2026-08-16
**Repository:** IntentLock V4
**Status:** Active roadmap — items are not completed unless marked otherwise

---

## 1. Docker Verification

**Status:** Workflow enhanced; CI execution pending

### Completed
- Enhanced `.github/workflows/docker-verify.yml` with checks for:
  - Docker Compose build
  - Service startup and healthcheck wait loop
  - PostgreSQL authentication (correct password acceptance, empty password rejection)
  - Redis authentication (correct password acceptance, unauthenticated rejection)
  - Application health (`/api/v1/health`) and readiness (`/api/v1/ready`) endpoints
  - Non-root UID verification (both image config and runtime exec)
  - `no-new-privileges` security option verification
  - tmpfs mount verification (`/tmp/intentlock` with `noexec,nosuid`)
  - Network isolation verification (single-bridge network attachment)
  - Secret exposure scan across application, venv, and system paths
  - Container restart behavior with health/ready re-verification
  - Volume removal verification after `docker compose down -v`
  - Ephemeral CI test credentials via `.env.test` (never committed)

### Remaining
- Execute workflow on GitHub Actions Ubuntu runner
- Verify all checks report PASS in CI
- Address any CI failures before declaring Docker verification complete

### Action
Push a branch to trigger `.github/workflows/docker-verify.yml` and capture the GitHub Actions run URL.

---

## 2. Git History Cleanup

**Status:** Runtime files staged for removal; history rewrite pending team approval

### Completed
- `git rm --cached intentlock.db logs/audit_trail.jsonl` executed
- `.gitignore` updated to explicitly exclude `.env.test` and lock files
- Both files removed from current working tree and index

### Remaining
- History rewrite using `git filter-repo` or BFG Repo-Cleaner
- Force-push after team coordination
- Team re-sync of local clones
- Verification that files are absent from all commits

### Action
Execute `docs/operations/GIT_HISTORY_REMEDIATION.md` after obtaining explicit approval from:
1. Repository maintainer
2. Security team
3. All active contributors

**Do NOT execute without written approval.**

---

## 3. KMS / HSM Integration

**Status:** Interface placeholders defined; production integration pending

### Current State
- `KMSKeyManager` and `HSMKeyProvider` interfaces exist
- `SimulatedHSMKeyProvider` used for testing
- Ed25519 keys currently stored on disk or generated ephemerally

### Milestones
1. **Evaluation** — Select KMS/HSM provider (AWS KMS, HashiCorp Vault, Azure Key Vault, or HSM appliance)
2. **Integration** — Implement production `HSMKeyProvider` backed by selected provider
3. **Key Rotation** — Automate key rotation with grace periods and zero-downtime signing
4. **Fallback Strategy** — Define failover behavior when KMS/HSM is unavailable
5. **Audit** — Log all key management operations (sign, verify, rotate, destroy)

### Action
Create a separate design document for KMS/HSM integration. Do not implement until provider is selected.

---

## 4. JWT Replay / Rotation / Revocation Strategy

**Status:** Architectural decision documented; implementation pending

### Current State
- Access tokens are stateless JWTs (HS256) with short expiration (default 30 min, max 24h)
- No server-side replay protection for access tokens
- Execution tokens use atomic nonce consumption (Redis-backed)

### Milestones
1. **Threat Model Update** — Document acceptable replay risk for access tokens in deployment context
2. **Replay Protection Options:**
   - Option A: Opaque access tokens with server-side session store (increases latency and complexity)
   - Option B: Short-lived JWTs (5-15 min) with refresh tokens (increases token churn)
   - Option C: Maintain current design with strict network controls and monitoring
3. **Revocation Strategy** — Implement token revocation list (Redis-backed) for compromised tokens
4. **Rotation Strategy** — Automated JWT secret rotation with graceful key transition
5. **Monitoring** — Alert on anomalous token usage patterns (geographic anomalies, rapid rotation)

### Action
Do not modify JWT implementation until the threat model and options are reviewed. Current design is acceptable for internal/trusted-network deployments with documented limitations.

---

## 5. Independent Penetration Testing

**Status:** Not started

### Scope
- Network-level access controls for intent endpoints
- Redis and PostgreSQL authentication in production deployments
- TLS configuration and certificate validation
- Real-world JWT and execution token attack scenarios
- Container escape and privilege escalation
- Supply chain attack vectors (dependency confusion, typosquatting)

### Milestones
1. **Vendor Selection** — Identify qualified security firm
2. **Scoping** — Define test boundaries, rules of engagement, and out-of-scope items
3. **Execution** — Conduct black-box and gray-box penetration testing
4. **Remediation** — Address findings with regression tests
5. **Re-test** — Verify all findings are resolved

### Action
Budget and schedule independent penetration testing before any production deployment in hostile network environments.

---

## 6. Threat Model Review

**Status:** Initial model documented; formal review pending

### Current Coverage
- Trust boundaries: Agent → Gateway, User → Gateway, Gateway → Redis, Gateway → Database, Gateway → External LLM/Tools
- Attack surfaces: authentication, authorization, rate limiting, input validation, key management, audit integrity
- Documented in `docs/security/SECURITY_ASSURANCE_REPORT.md` and `docs/architecture/ARCHITECTURE.md`

### Milestones
1. **Formal Review** — Conduct structured threat modeling session (STRIDE or PASTA methodology)
2. **Attack Tree Expansion** — Document concrete attack paths for each threat
3. **Mitigation Mapping** — Map each threat to implemented or planned controls
4. **Residual Risk Acceptance** — Document accepted risks with rationale
5. **Periodic Review** — Schedule annual or per-release threat model updates

### Action
Schedule a formal threat modeling session before the next major release.

---

## 7. Enterprise Deployment Security

**Status:** Guidelines documented; production hardening pending

### Current Coverage
- Docker image hardening (non-root, tmpfs, no-new-privileges)
- Redis authentication and health checks
- PostgreSQL parameterized credentials
- Multi-tenancy isolation
- Compliance evidence export

### Milestones
1. **Secrets Management** — Integrate HashiCorp Vault, AWS Secrets Manager, or equivalent
2. **TLS Everywhere** — Enforce TLS 1.3 on all external and internal communications
3. **Network Segmentation** — Deploy in private subnets with strict firewall rules
4. **Log Aggregation** — Ship audit logs to SIEM (Splunk, ELK, Datadog)
5. **Observability** — Implement distributed tracing (OpenTelemetry) and alerting
6. **Backup and DR** — Automated PostgreSQL backups with point-in-time recovery
7. **Access Control** — Integrate with corporate IAM (OIDC/SAML/OAuth2)
8. **Image Signing** — Sign Docker images and enforce verification in deployment

### Action
Create an `ENTERPRISE_DEPLOYMENT.md` with environment-specific hardening steps.

---

## 8. Compliance Readiness

**Status:** No compliance assessment performed

### Current Coverage
- HMAC-signed compliance evidence export
- Hash-chain audit integrity
- RBAC and HITL logging

### Milestones
1. **Gap Analysis** — Map current controls to HIPAA, PCI-DSS, SOC 2, and GDPR requirements
2. **Policy Documentation** — Create privacy policy, data retention policy, incident response plan
3. **Access Reviews** — Quarterly access reviews and least-privilege audits
4. **Audit Trail** — Ensure 100% coverage of security-relevant events
5. **Independent Audit** — Engage auditor for SOC 2 Type II or equivalent assessment
6. **Certification** — Obtain and maintain relevant certifications

### Action
Do not claim HIPAA, PCI, SOC 2, or any regulatory compliance without a completed independent assessment.

---

## Summary

| Area | Status | Next Action |
|------|--------|-------------|
| Docker Verification | Workflow complete; CI pending | Push to trigger GitHub Actions |
| Git History Cleanup | Procedure documented; pending approval | Obtain team approval before rewrite |
| KMS/HSM Integration | Interfaces defined | Select provider and design integration |
| JWT Strategy | Documented | Threat model review before changes |
| Penetration Testing | Not started | Budget and schedule |
| Threat Model Review | Initial draft | Formal session before next release |
| Enterprise Deployment | Guidelines documented | Create runbook and integrate secrets management |
| Compliance Readiness | No assessment | Gap analysis and independent audit |

---

## Important Disclaimers

- IntentLock V4 is **not** "10/10 secure", "certified", "bank-grade", "HIPAA compliant", "PCI compliant", or "SOC 2 compliant" without independent evidence.
- This roadmap does not guarantee security outcomes. Implementation must be validated through testing and independent assessment.
- All timeline estimates are subject to change based on resource availability and emerging threats.
