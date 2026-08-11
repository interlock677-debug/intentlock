from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency fallback
    yaml = None


@dataclass
class PolicyEngine:
    """Deterministic policy evaluation engine.

    Evaluates text against configurable blocked patterns and risk markers.
    Supports YAML configuration via `config/policies.yaml`.
    """

    score_threshold: float = 0.5
    blocked_patterns: list[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: str | Path | None = None) -> PolicyEngine:
        policy_path = Path(
            path or os.getenv("POLICY_FILE_PATH") or cls._default_policy_path(),
        )
        payload: dict[str, Any] = {}

        if policy_path.exists():
            if yaml is not None:
                with policy_path.open("r", encoding="utf-8") as handle:
                    payload = yaml.safe_load(handle) or {}
            else:
                payload = cls._parse_simple_yaml(policy_path)

        threshold = float(payload.get("score_threshold", 0.5))
        raw_patterns = payload.get("blocked_patterns", [])
        patterns = [
            str(item).strip().lower()
            for item in raw_patterns
            if str(item).strip()
        ]
        return cls(score_threshold=threshold, blocked_patterns=patterns)

    def evaluate(self, text: str) -> dict[str, Any]:
        normalized = (text or "").lower()
        reasons: list[str] = []
        score = 0.0

        for pattern in self.blocked_patterns:
            if pattern in normalized:
                score += 0.35
                reasons.append(f"Blocked pattern matched: {pattern}")

        if self._contains_zero_width(text):
            score += 0.35
            reasons.append("Zero-width unicode characters detected")

        if self._looks_like_base64(text):
            score += 0.35
            reasons.append("Base64 payload detected")

        if "transfer" in normalized and "$" in text:
            score += 0.15
            reasons.append("Financial transfer pattern detected")

        if not reasons:
            reasons.append("No suspicious markers detected")

        risk_score = round(min(score, 1.0), 3)
        has_blocked = any("Blocked pattern matched" in r for r in reasons)
        blocked = risk_score >= self.score_threshold or has_blocked
        return {
            "risk_score": risk_score,
            "blocked": blocked,
            "requires_approval": blocked or risk_score >= self.score_threshold,
            "reasons": reasons,
        }

    @staticmethod
    def _default_policy_path() -> Path:
        return Path(__file__).resolve().parents[2] / "config" / "policies.yaml"

    @staticmethod
    def _contains_zero_width(text: str) -> bool:
        return any(char in text for char in {"\u200b", "\u200c", "\u200d", "\ufeff"})

    @staticmethod
    def _looks_like_base64(text: str) -> bool:
        if not text:
            return False
        base64_like = re.findall(r"(?:[A-Za-z0-9+/]{8,}={0,2})", text)
        return any(
            candidate
            for candidate in base64_like
            if (len(candidate) >= 8 and "=" in candidate)
            or len(candidate) >= 12
        )

    @staticmethod
    def _parse_simple_yaml(path: Path) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        current_key: str | None = None
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.endswith(":") and not line.startswith("- "):
                current_key = line[:-1]
                payload[current_key] = [] if current_key == "blocked_patterns" else {}
                continue
            if line.startswith("- ") and current_key == "blocked_patterns":
                payload[current_key].append(line[2:].strip().strip("\"'"))
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                payload[key.strip()] = value.strip().strip("\"'")
        return payload
