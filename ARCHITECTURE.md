# IntentLock Architecture

## 1. System Overview

IntentLock is a lightweight proof-of-intent authorization gateway for AI agents. It provides a deterministic, low-latency verification layer that intercepts proposed agent actions before execution and enforces policy using a local runtime.

The gateway is designed for enterprise environments where AI agents must be constrained by strict security controls, auditability, and minimal external dependency.

Key characteristics:
- Lightweight and fast, with minimal runtime overhead.
- Zero-latency verification for local agent workflows.
- Proof-of-intent semantics: the agent must demonstrate the requested action before execution.
- Works as a local gateway to prevent unsafe or unauthorized behavior.

## 2. Zero-Trust Data Flow Diagram

User Prompt -> Agent Reasoning -> IntentLock Gateway -> 1-Second Ephemeral Token -> Enterprise Resource

Detailed flow:

1. User Prompt
   - The user provides an instruction, goal, or query to the AI agent.
2. Agent Reasoning
   - The agent selects a tool and prepares a proposed action with tool name and arguments.
3. IntentLock Gateway
   - The SDK posts the proposed action to `/api/v1/intent/verify`.
   - IntentLock evaluates the request against deterministic policies.
4. 1-Second Ephemeral Token
   - If allowed, the gateway returns a single-use JWT valid for 1 second.
5. Enterprise Resource
   - The agent uses the ephemeral token to execute the action against the protected resource.

## 3. Security Guarantees

- Single-use 1-second JWT execution tokens.
  - Execution tokens expire immediately after issuance and are valid for only one second.

- Deterministic policy enforcement.
  - SQL injection and destructive query patterns are detected using deterministic rule checks.
  - Financial action limits are enforced based on prompt instructions and tool arguments.

- Local execution with zero external internet data egress.
  - IntentLock is built for on-premise or air-gapped deployment.
  - No external AI request or data exfiltration is required for verification.

- Structured JSON audit logging.
  - Verification decisions are recorded in `logs/audit_trail.jsonl`.
  - JSONL format enables easy ingestion into SIEM tools such as Splunk, Datadog, or other security analytics platforms.

## 4. Deployment Options

### On-Premise Docker

The application can run locally or on-premise using Docker Compose.

```bash
docker compose up --build
```

This deployment option is ideal for enterprise environments requiring strong network controls and full infrastructure ownership.

### Cloud Run / VPC Deployment

For managed cloud deployment, run the gateway in a VPC-enabled environment and restrict access to trusted agents only.

1. Build a container image.
2. Deploy into a VPC or private subnet.
3. Configure ingress rules so only approved agent hosts may call the verification endpoint.
4. Ensure audit logs are forwarded to enterprise monitoring and SIEM.

This approach preserves the zero-trust architecture while enabling managed cloud operations.

## 5. Integration Guide

### IntentLockGuard SDK

Use `IntentLockGuard` to protect Python-based tool calls with IntentLock verification.

```python
from sdk.intentlock import IntentLockGuard

intent_lock = IntentLockGuard()

@intent_lock.guard_tool(intent_lock)
def transfer_funds(amount: int, recipient: str, user_prompt: str, agent_id: str):
    # execute payment
    return f"Transferred ${amount} to {recipient}"
```

### IntentLockLangChainTool

Use `IntentLockLangChainTool` to wrap LangChain tools with the same IntentLock verification flow.

```python
from sdk.langchain_adapter import IntentLockLangChainTool

def my_tool(query: str, user_prompt: str, agent_id: str):
    return f"Query executed: {query}"

wrapped_tool = IntentLockLangChainTool(my_tool)
result = wrapped_tool(
    "SELECT * FROM users",
    user_prompt="Run a safe analytics query",
    agent_id="agent-123",
)
```

The adapter sends the proposed tool name, prompt, reasoning step, and arguments to the IntentLock gateway and blocks execution if a security policy is violated.
