# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 4.x     | :white_check_mark: |

## Reporting a Vulnerability

IntentLock takes security seriously. If you discover a security vulnerability, please report it responsibly.

### How to report

Send details to **security@intentlock.io** with:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested remediation (if any)

### What to expect

- Acknowledgment within 5 business days
- A more detailed response within 10 business days outlining remediation plans
- Credit in the security advisory (unless you prefer anonymity)

### Scope

In-scope for reporting includes:

- Authentication and authorization bypasses
- Token forgery or replay attacks
- SQL injection, shell injection, or path traversal
- SSRF or DNS rebinding
- Prompt injection or policy bypass
- Audit log tampering
- Dependency vulnerabilities in runtime dependencies
- Docker image security issues

Out of scope:

- Social engineering of IntentLock employees or users
- Physical security of data centers
- Issues in third-party dependencies that are not exploitable in IntentLock
- Denial of service without a demonstrated security impact

### Safe harbor

IntentLock will not pursue legal action against researchers who:

- Report vulnerabilities in good faith
- Avoid privacy violations, data destruction, or service disruption
- Do not exploit vulnerabilities beyond what is necessary to prove the issue
