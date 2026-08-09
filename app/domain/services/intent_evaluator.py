import re
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.domain.models.intent import AgentActionDAG, IntentProofResponse
from app.infrastructure.config.settings import get_settings


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

        return IntentProofResponse(
            is_valid=True,
            confidence_score=0.95,
            reason="Intent appears safe for execution.",
        )

    def create_execution_token(self, intent: AgentActionDAG) -> str:
        settings = get_settings()
        now = datetime.now(tz=timezone.utc)
        payload = {
            "sub": intent.agent_id,
            "type": "execution",
            "tool": intent.proposed_tool,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=1)).timestamp()),
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def _inspect_destructive_sql(self, intent: AgentActionDAG) -> str | None:
        arguments = self._collect_strings(intent.tool_arguments)
        sql_text = " ".join(arguments)

        for pattern in DESCTRUCTIVE_SQL_PATTERNS:
            if re.search(pattern, sql_text, flags=re.IGNORECASE):
                return "Destructive SQL detected in proposed tool action."

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
                f"Requested transfer amount ${transfer_amount:.2f} exceeds the prompt limit of ${prompt_limit:.2f}."
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
            if isinstance(value, str) and re.search(r"\$\d", value):
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
