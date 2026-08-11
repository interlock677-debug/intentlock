from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VelocityWindow:
    """Sliding-window state for a single scope (agent, identity, tenant)."""

    request_timestamps: deque[float] = field(default_factory=deque)
    cumulative_value: float = 0.0
    cumulative_risk: float = 0.0
    sensitive_operations: int = 0


class VelocityTracker:
    """Stateful sliding-window security controls.

    Tracks request velocity, cumulative financial value, cumulative risk
    score, and repeated sensitive operations per scope. All thresholds
    are configurable — no hardcoded financial limits.
    """

    def __init__(
        self,
        *,
        window_seconds: int = 60,
        max_requests: int = 100,
        max_cumulative_value: float = 10_000.0,
        max_cumulative_risk: float = 5.0,
        max_sensitive_operations: int = 10,
    ) -> None:
        self._window_seconds = window_seconds
        self._max_requests = max_requests
        self._max_cumulative_value = max_cumulative_value
        self._max_cumulative_risk = max_cumulative_risk
        self._max_sensitive_operations = max_sensitive_operations
        self._windows: dict[str, VelocityWindow] = defaultdict(VelocityWindow)
        self._lock = threading.Lock()

    def record(
        self,
        *,
        scope: str,
        value: float = 0.0,
        risk_score: float = 0.0,
        is_sensitive: bool = False,
    ) -> dict[str, Any]:
        """Record an event and return the current window state."""
        with self._lock:
            now = time.monotonic()
            window = self._windows[scope]
            self._prune(window, now)

            window.request_timestamps.append(now)
            window.cumulative_value += value
            window.cumulative_risk += risk_score
            if is_sensitive:
                window.sensitive_operations += 1

            return self._evaluate(scope, window, now)

    def get_state(self, scope: str) -> dict[str, Any]:
        """Return the current state for a scope without recording."""
        with self._lock:
            now = time.monotonic()
            window = self._windows.get(scope)
            if window is None:
                return {
                    "scope": scope,
                    "request_count": 0,
                    "cumulative_value": 0.0,
                    "cumulative_risk": 0.0,
                    "sensitive_operations": 0,
                    "blocked": False,
                    "reasons": [],
                }
            self._prune(window, now)
            return self._evaluate(scope, window, now)

    def reset(self, scope: str | None = None) -> None:
        with self._lock:
            if scope is None:
                self._windows.clear()
            else:
                self._windows.pop(scope, None)

    def _prune(self, window: VelocityWindow, now: float) -> None:
        cutoff = now - self._window_seconds
        while window.request_timestamps and window.request_timestamps[0] < cutoff:
            window.request_timestamps.popleft()

    def _evaluate(self, scope: str, window: VelocityWindow, now: float) -> dict[str, Any]:
        self._prune(window, now)
        request_count = len(window.request_timestamps)
        reasons: list[str] = []

        if request_count > self._max_requests:
            reasons.append(
                f"Request velocity exceeded: {request_count} > {self._max_requests}"
            )

        if window.cumulative_value > self._max_cumulative_value:
            reasons.append(
                f"Cumulative value exceeded: "
                f"${window.cumulative_value:.2f} > "
                f"${self._max_cumulative_value:.2f}"
            )

        if window.cumulative_risk > self._max_cumulative_risk:
            reasons.append(
                f"Cumulative risk exceeded: "
                f"{window.cumulative_risk:.2f} > {self._max_cumulative_risk:.2f}"
            )

        if window.sensitive_operations > self._max_sensitive_operations:
            reasons.append(
                f"Sensitive operations exceeded: "
                f"{window.sensitive_operations} > {self._max_sensitive_operations}"
            )

        return {
            "scope": scope,
            "request_count": request_count,
            "cumulative_value": round(window.cumulative_value, 2),
            "cumulative_risk": round(window.cumulative_risk, 2),
            "sensitive_operations": window.sensitive_operations,
            "blocked": bool(reasons),
            "reasons": reasons,
        }
