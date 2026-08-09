import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_PATH = Path("logs") / "audit_trail.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("intentlock.audit")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "{\"timestamp\": \"%(asctime)s\", \"agent_id\": \"%(agent_id)s\", \"proposed_tool\": \"%(proposed_tool)s\", \"tool_arguments\": %(tool_arguments)s, \"verification_status\": \"%(verification_status)s\", \"rejection_reason\": \"%(rejection_reason)s\"}"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def log_verification(
    agent_id: str,
    proposed_tool: str,
    tool_arguments: dict[str, Any],
    verification_status: str,
    rejection_reason: str = "",
) -> None:
    record = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "agent_id": agent_id,
        "proposed_tool": proposed_tool,
        "tool_arguments": tool_arguments,
        "verification_status": verification_status,
        "rejection_reason": rejection_reason,
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    logger.info(
        "audit",
        extra={
            "agent_id": agent_id,
            "proposed_tool": proposed_tool,
            "tool_arguments": json.dumps(tool_arguments),
            "verification_status": verification_status,
            "rejection_reason": rejection_reason,
        },
    )
