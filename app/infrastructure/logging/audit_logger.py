import hashlib
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_PATH = PROJECT_ROOT / "logs" / "audit_trail.jsonl"
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
    jti: str | None = None,
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
        "jti": jti or "",
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


def log_compliance_event(
    event_type: str,
    *,
    correlation_id: str | None = None,
    **details: Any,
) -> None:
    """Write a tamper-evident compliance audit record.

    Each record includes a hash chain pointer to the previous record
    for integrity verification.
    """
    record: dict[str, Any] = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "event_type": event_type,
        "correlation_id": correlation_id or "",
    }
    record.update(details)

    last_hash = _get_last_hash()
    record["previous_hash"] = last_hash
    record["hash"] = _compute_hash(record)

    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    logger.info(json.dumps(record))


def _get_last_hash() -> str:
    if not LOG_PATH.exists():
        return ""
    try:
        with LOG_PATH.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()
        if not lines:
            return ""
        last_line = lines[-1].strip()
        if not last_line:
            return ""
        last_record = json.loads(last_line)
        return str(last_record.get("hash", ""))
    except Exception:
        return ""


def _compute_hash(record: dict[str, Any]) -> str:
    filtered = {k: v for k, v in record.items() if k not in ("previous_hash", "hash")}
    payload = json.dumps(filtered, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def export_audit_log(output_path: str) -> dict[str, Any]:
    """Export audit records to a JSON file with integrity hash chain.

    Returns a summary dict with export metadata.
    """
    records: list[dict[str, Any]] = []
    if LOG_PATH.exists():
        with LOG_PATH.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

    chain_valid = _verify_hash_chain(records)

    export_payload = {
        "exported_at": datetime.now(tz=UTC).isoformat(),
        "record_count": len(records),
        "chain_valid": chain_valid,
        "records": records,
    }

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(export_payload, handle, indent=2, default=str)

    return {
        "output_path": output_path,
        "record_count": len(records),
        "chain_valid": chain_valid,
    }


def get_audit_evidence(
    since: str | None = None,
    until: str | None = None,
) -> dict[str, Any]:
    """Generate a reproducible evidence package from audit records.

    Filters records by optional time range and includes integrity proof.
    """
    records: list[dict[str, Any]] = []
    if LOG_PATH.exists():
        with LOG_PATH.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                ts = record.get("timestamp", "")
                if since and ts < since:
                    continue
                if until and ts > until:
                    continue
                records.append(record)

    chain_valid = _verify_hash_chain(records)

    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "filter": {"since": since, "until": until},
        "record_count": len(records),
        "chain_valid": chain_valid,
        "records": records,
    }


def _verify_hash_chain(records: list[dict[str, Any]]) -> bool:
    if not records:
        return True
    for i, record in enumerate(records):
        expected_prev = record.get("previous_hash", "")
        record_hash = record.get("hash", "")
        if i == 0:
            if expected_prev != "":
                return False
        else:
            prev_record = records[i - 1]
            actual_prev = prev_record.get("hash", "")
            if expected_prev != actual_prev:
                return False
        computed = _compute_hash_without_hash_fields(record)
        if computed != record_hash:
            return False
    return True


def _compute_hash_without_hash_fields(record: dict[str, Any]) -> str:
    filtered = {k: v for k, v in record.items() if k not in ("previous_hash", "hash")}
    payload = json.dumps(filtered, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
