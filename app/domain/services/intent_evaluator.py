import ast
import re
from typing import Any

import sqlglot

from app.domain.models.intent import AgentActionDAG, IntentProofResponse
from app.domain.services.policy_engine import PolicyEngine

DESCTRUCTIVE_SQL_PATTERNS = [
    r"\bDROP\s+TABLE\b",
    r"\bTRUNCATE\s+TABLE\b",
    r"\bDELETE\s+FROM\b(?!.*\bWHERE\b).*",
    r"\bUPDATE\b(?!.*\bWHERE\b).*",
]

TRANSFER_KEYWORDS = ["transfer", "payment", "send", "withdraw", "deposit"]

MAX_AMOUNT_PROMPT_PATTERNS = [
    r"(?:limit|maximum|max|up to|no more than|not exceed)\s*\$?([0-9][0-9,]*(?:\.[0-9]+)?)",
    r"\$([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:or less|or under|or fewer)",
]


class IntentEvaluatorService:
    """Evaluates agent intents for proof-of-intent authorization."""

    def __init__(self, policy_engine: PolicyEngine | None = None) -> None:
        self._policy_engine = policy_engine or PolicyEngine.from_file()

    def evaluate(self, intent: AgentActionDAG) -> IntentProofResponse:
        destructive_reason = self._inspect_destructive_sql(intent)
        if destructive_reason:
            return IntentProofResponse(
                is_valid=False,
                confidence_score=0.0,
                reason=destructive_reason,
            )

        transfer_reason = self._inspect_financial_transfer(intent)
        if transfer_reason:
            return IntentProofResponse(
                is_valid=False,
                confidence_score=0.2,
                reason=transfer_reason,
            )

        # Policy engine risk evaluation
        policy_text = f"{intent.user_prompt} {intent.reasoning_step}"
        policy_result = self._policy_engine.evaluate(policy_text)
        if policy_result.get("blocked"):
            reasons = "; ".join(str(r) for r in policy_result.get("reasons", []))
            return IntentProofResponse(
                is_valid=False,
                confidence_score=float(policy_result.get("risk_score", 0.0)),
                reason=f"Policy violation: {reasons}",
            )

        # Polyglot/shell payload detection
        if self._contains_polyglot_payload(intent):
            return IntentProofResponse(
                is_valid=False,
                confidence_score=0.5,
                reason="Polyglot or shell payload detected in proposed tool action.",
            )

        return IntentProofResponse(
            is_valid=True,
            confidence_score=0.95,
            reason="Intent appears safe for execution.",
        )

    def _inspect_destructive_sql(self, intent: AgentActionDAG) -> str | None:
        arguments = self._collect_strings(intent.tool_arguments)
        sql_text = " ".join(arguments)

        for pattern in DESCTRUCTIVE_SQL_PATTERNS:
            if re.search(pattern, sql_text, flags=re.IGNORECASE):
                return "Destructive SQL detected in proposed tool action."

        # Use sqlglot to detect SQL injection attempts
        try:
            parsed = sqlglot.parse_one(sql_text)
            if parsed is not None:
                sql_type = str(parsed.key).upper()
                if sql_type in {"DROP", "TRUNCATE", "DELETE", "UPDATE"}:
                    return "Destructive SQL detected by parser."
        except Exception:
            return None

        return None

    def _inspect_financial_transfer(self, intent: AgentActionDAG) -> str | None:
        prompt_limit = self._extract_prompt_limit(intent.user_prompt)
        if prompt_limit is None:
            return None

        if not self._is_transfer_action(intent.proposed_tool, intent.tool_arguments):
            return None

        transfer_amount = self._extract_transfer_amount(intent.tool_arguments)
        if transfer_amount is None:
            return None

        if transfer_amount > prompt_limit:
            return (
                f"Requested transfer amount ${transfer_amount:.2f} exceeds the prompt limit "
                f"of ${prompt_limit:.2f}."
            )

        return None

    def _is_transfer_action(self, tool_name: str, tool_arguments: dict[str, Any]) -> bool:
        lowered = tool_name.lower()
        if any(keyword in lowered for keyword in TRANSFER_KEYWORDS):
            return True
        argument_keys = " ".join(str(key).lower() for key in tool_arguments)
        return any(keyword in argument_keys for keyword in TRANSFER_KEYWORDS)

    def _extract_prompt_limit(self, prompt: str) -> float | None:
        for pattern in MAX_AMOUNT_PROMPT_PATTERNS:
            match = re.search(pattern, prompt, flags=re.IGNORECASE)
            if match:
                return self._parse_amount(match.group(1))
        return None

    def _extract_transfer_amount(self, arguments: dict[str, Any]) -> float | None:
        for key, value in arguments.items():
            if key.lower() in ("amount", "value", "total", "transfer_amount", "payment_amount"):
                return self._parse_amount(value)
            if isinstance(value, str):
                found = re.search(r"\$([0-9][0-9,]*(?:\.[0-9]+)?)", value)
                if found:
                    return self._parse_amount(found.group(1))
        return None

    def _parse_amount(self, amount: Any) -> float | None:
        if amount is None:
            return None
        if isinstance(amount, (int, float)):
            return float(amount)
        text = str(amount).replace(",", "")
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
        if not match:
            return None
        return float(match.group(1))

    def _collect_strings(self, value: Any) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            result: list[str] = []
            for item in value.values():
                result.extend(self._collect_strings(item))
            return result
        if isinstance(value, list):
            result = []
            for item in value:
                result.extend(self._collect_strings(item))
            return result
        return []

    def _contains_polyglot_payload(self, intent: AgentActionDAG) -> bool:
        text = f"{intent.user_prompt} {intent.reasoning_step}"
        if re.search(
            r"union\s+select|drop\s+table|truncate\s+table|echo\s+",
            text,
            flags=re.IGNORECASE,
        ):
            return True
        try:
            sqlglot.parse_one(text)
            return True
        except Exception:
            try:
                ast.parse(text)
                return True
            except Exception:
                return False
        return True
