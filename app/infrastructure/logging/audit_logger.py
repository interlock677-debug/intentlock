import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LOG_PATH = Path("logs") / "audit_trail.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("intentlock.audit")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


def log_verification(
    agent_id: str,
    proposed_tool: str,
    tool_arguments: dict[str, Any],
    verification_status: str,
    rejection_reason: str = "",
    *,
    correlation_id: str | None = None,
) -> None:
    """Write a structured audit record for intent verification.

    Never logs secrets, tokens, or sensitive request data.
    """
    record = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "event_type": "intent_verification",
        "correlation_id": correlation_id or "",
        "agent_id": agent_id,
        "proposed_tool": proposed_tool,
        "verification_status": verification_status,
        "rejection_reason": rejection_reason,
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    logger.info(json.dumps(record))


def log_security_event(
    event_type: str,
    *,
    correlation_id: str | None = None,
    **details: Any,
) -> None:
    """Write a structured security event record.

    Never logs secrets, tokens, or sensitive request data.
    """
    record: dict[str, Any] = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "event_type": event_type,
        "correlation_id": correlation_id or "",
    }
    record.update(details)

    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    logger.info(json.dumps(record))
