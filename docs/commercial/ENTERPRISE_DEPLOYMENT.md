# Enterprise Deployment Guide

Production-grade deployment patterns for IntentLock in regulated, multi-tenant, or high-availability environments.

> **Note:** This guide references adapter ports and placeholder interfaces for enterprise integrations. SAML, OIDC, SIEM, ticketing, and KMS/HSM integrations are implemented as mock adapters and interface placeholders. Production deployments require actual integration with external systems.

## Contents

- [Architecture patterns](#architecture-patterns)
- [Secrets management](#secrets-management)
- [Key management](#key-management)
- [Network topology](#network-topology)
- [Database and Redis](#database-and-redis)
- [Observability](#observability)
- [Compliance](#compliance)
- [Disaster recovery](#disaster-recovery)
- [Kubernetes](#kubernetes)
- [Security hardening](#security-hardening)

---

## Architecture patterns

### Single-region, single-tenant

```
                    ┌──────────────┐
                    │ Load Balancer│
                    │ (TLS term)   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ IntentLock   │
                    │ Gateway      │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐
        │ PostgreSQL│ │ Redis  │ │   SIEM   │
        │  (data)   │ │(nonce) │ │ (forward)│
        └───────────┘ └────────┘ └──────────┘
```

Use case: Single business unit, single region, no multi-tenancy.

### Multi-tenant, multi-region

```
    ┌────────────┐     ┌────────────┐     ┌────────────┐
    │ Region: US  │     │ Region: EU │     │ Region: APAC│
    └──────┬──────┘     └──────┬─────┘     └──────┬──────┘
           │                   │                   │
    ┌──────▼───────────────────▼───────────────────▼──────┐
    │                Global Control Plane                 │
    │           (policy, keys, audit aggregation)         │
    └──────────────────────────────────────────────────────┘
```

Use case: SaaS platform with tenant isolation and regional data residency.

### Air-gapped / on-prem

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Agent      │────▶│  IntentLock  │────▶│  HSM / KMS  │
│  Runtime    │     │  Appliance   │     │  (signing)  │
└─────────────┘     └──────┬───────┘     └─────────────┘
                            │
                     ┌──────▼───────┐
                     │  PostgreSQL  │
                     │  (local)     │
                     └──────────────┘
```

Use case: Classified environments, financial trading floors, healthcare on-prem.

---

## Secrets management

Never store secrets in environment variables or configuration files in production. Use one of:

- **HashiCorp Vault** — dynamic secrets, lease management, audit logging
- **AWS Secrets Manager** — rotation, Lambda rotation hooks, IAM integration
- **Azure Key Vault** — HSM-backed keys, managed identities
- **Kubernetes Secrets** — sealed with Sealed Secrets or external-secrets operator

Required secrets:

| Secret | Purpose | Rotation |
|--------|---------|----------|
| `JWT_SECRET_KEY` | HS256 access token signing | 90 days |
| `compliance_secret_key` | HMAC integrity for evidence exports | 90 days |
| `REDIS_PASSWORD` | Redis authentication | 30 days |
| `POSTGRES_PASSWORD` | PostgreSQL authentication | 90 days |
| `EXECUTION_KEY_PATH` | Ed25519 signing key (or KMS reference) | 30 days |

---

## Key management

### Ephemeral keys (development)

Keys are generated in-process and lost on restart. Tokens signed before restart become invalid. Suitable only for development.

### File-backed keys (staging / single-instance)

Set `EXECUTION_KEY_PATH=/secure/keys/execution.pem`. Keys persist across restarts but do not span instances.

### KMS / HSM (production enterprise)

Configure `KMS_KEY_MANAGER_CLASS` with a provider-specific settings. The `VersionedKeyManager` interface is a placeholder for external KMS/HSM integration:

- **AWS KMS:** `KMS_KEY_ID=arn:aws:kms:...`
- **HashiCorp Vault:** `VAULT_ADDR`, `VAULT_TOKEN`, `VAULT_KEY_PATH`
- **Azure Key Vault:** `AZURE_KEY_VAULT_URL`, `AZURE_KEY_NAME`
- **HSM appliance:** PKCS#11 provider configuration

External KMS/HSM providers delegate signing to the external provider. `VersionedKeyManager` still manages key versioning and grace periods.

---

## Network topology

### Ingress

- TLS termination at load balancer or ingress controller
- Restrict `/api/v1/intent/*` to authorized agent subnets or service mesh
- `/api/v1/auth/*` and `/api/v1/approval/*` exposed to corporate IdP or VPN
- `/api/v1/health` and `/api/v1/ready` exposed to load balancer health checks only

### Egress

- Gateway requires outbound access to PostgreSQL and Redis
- No outbound internet required in air-gapped deployments
- Audit logs forwarded to SIEM via syslog, HTTP, or Kafka adapter

### Service mesh (optional)

Deploy behind Istio or Linkerd for mTLS, retries, and circuit breaking. IntentLock remains stateless; mesh sidecars handle transport security.

---

## Database and Redis

### PostgreSQL

- Run with SSL enabled for data in transit
- Use PgBouncer for connection pooling at high scale
- Enable `log_statement = 'all'` for forensic audit (separate from IntentLock audit log)
- Backup: continuous WAL archiving + point-in-time recovery
- Schema owned by `intentlock` role with least privilege

### Redis

- Require authentication (`--requirepass` or AUTH)
- Disable `CONFIG` command (`rename-command CONFIG ""`)
- Enable TLS for remote connections
- Use Redis Sentinel or Cluster for HA
- Persistence: AOF + RDB snapshots
- Network: bind to private interface only; firewall to application subnet

---

## Observability

### Metrics

Expose `/api/v1/metrics` (admin-only) or integrate with the monitoring adapter:

```python
from app.infrastructure.integrations.monitoring_adapter import MonitoringAdapter, MetricType

adapter = MonitoringAdapter(enabled=True)
adapter.record(MetricType.COUNTER, "intent_verified", 1, {"tool": "database_query"})
adapter.record(MetricType.HISTOGRAM, "intent_latency_seconds", 0.05, {})
```

### Logging

- JSONL audit logs forwarded to centralized storage (S3, GCS, Azure Blob)
- Log retention per regulatory requirement (1 year recommended for enterprise)
- Correlation ID propagated in all log lines and traces

### Tracing

- Instrument with OpenTelemetry (placeholder; requires instrumentation implementation)
- Trace spans: `intent.verify`, `intent.execute`, `policy.evaluate`, `hitl.approve`
- Export to Jaeger, Honeycomb, or vendor APM

---

## Compliance

### Evidence export

```bash
curl -X POST http://localhost:8000/api/v1/compliance/export \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "2026-01-01T00:00:00Z",
    "end_time": "2026-01-31T23:59:59Z",
    "event_types": ["intent_verification", "hitl_approval"],
    "include_redacted": true
  }'
```

Export produces a tamper-evident package with HMAC integrity.

### Retention

| Data | Default retention | Recommended enterprise |
|------|------------------|------------------------|
| Audit log (JSONL) | 7 days | 1 year |
| Compliance evidence | Generated on request | 1 year |
| HITL requests | 24h TTL (configurable) | 90 days |
| Execution token records | 1 hour TTL | 7 days |

### Audit

- Quarterly access review of `hitl_approver_roles`
- Annual key rotation for `JWT_SECRET_KEY` and `compliance_secret_key`
- Annual penetration test (included in Enterprise tier)
- Log all administrative actions (policy changes, key rotation, user role changes)

---

## Disaster recovery

### RPO / RTO targets

| Scenario | RPO | RTO |
|----------|-----|-----|
| Gateway process crash | 0 (stateless) | < 30 seconds |
| PostgreSQL failure | < 5 minutes | < 5 minutes |
| Redis failure | N/A (fail-closed) | < 30 seconds |
| Regional outage | < 1 hour | < 1 hour |

### Backup strategy

- PostgreSQL: continuous archiving + weekly base backups + monthly restore test
- Redis: AOF rewrite every minute + daily RDB snapshot
- Configuration and policies: Git-backed, reviewed via PR
- Keys: backed up to HSM or secure offline storage

### Runbook

1. Detect failure via readiness endpoint (`/api/v1/ready`) or load balancer health check
2. Restart gateway pods / processes (stateless; no data loss)
3. Promote PostgreSQL replica if primary is unavailable
4. Restore Redis from AOF if data loss occurred
5. Rotate `JWT_SECRET_KEY` if exposure is suspected
6. Investigate via correlation IDs in audit logs

---

## Kubernetes

### Deployment manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: intentlock
  labels:
    app: intentlock
spec:
  replicas: 3
  selector:
    matchLabels:
      app: intentlock
  template:
    metadata:
      labels:
        app: intentlock
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: intentlock
          image: intentlock:4.0.0
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: intentlock-secrets
                  key: database-url
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: intentlock-secrets
                  key: redis-url
            - name: JWT_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: intentlock-secrets
                  key: jwt-secret
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
          readinessProbe:
            httpGet:
              path: /api/v1/ready
              port: 8000
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir:
            medium: Memory
            sizeLimit: "100Mi"
```

### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: intentlock
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/limit-connections: "100"
spec:
  tls:
    - hosts:
        - intentlock.example.com
      secretName: intentlock-tls
  rules:
    - host: intentlock.example.com
      http:
        paths:
          - path: /api/v1/intent
            pathType: Prefix
            backend:
              service:
                name: intentlock
                port:
                  number: 8000
```

---

## Security hardening

- Run containers as non-root (`runAsNonRoot: true`, `runAsUser: 1000`)
- Mount `/tmp` as `emptyDir` with `medium: Memory` and `sizeLimit`
- Set `allowPrivilegeEscalation: false` and `readOnlyRootFilesystem: true`
- Use image digest pinning (e.g., `intentlock@sha256:...`) instead of mutable tags
- Enable PodSecurity Standards (`restricted` profile)
- Scan images with Trivy or Grype in CI/CD
- Sign images with Sigstore / Cosign and enforce `ImagePolicy` in admission controller (requires implementation)

---

## Support and escalation

- **Free / Pro:** GitHub Issues and community Slack
- **Business:** Priority email/chat with named CSM
- **Enterprise:** 24x7 phone/email/Slack with named TAM and SRE escalation

For deployment architecture review, contact enterprise@intentlock.io.
