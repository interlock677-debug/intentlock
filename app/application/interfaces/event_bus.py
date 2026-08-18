from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class AuthorizationDeniedEvent:
    agent_id: str
    proposed_tool: str
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    correlation_id: str = ""


@dataclass(frozen=True)
class HITLEvent:
    request_id: str
    event_type: str
    decided_by: str | None = None
    risk_score: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    correlation_id: str = ""


@dataclass(frozen=True)
class PolicyDecisionEvent:
    rule_id: str
    effect: str
    reason: str
    agent_id: str = ""
    proposed_tool: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    correlation_id: str = ""


@dataclass(frozen=True)
class SecurityExceptionEvent:
    exception_type: str
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    correlation_id: str = ""


class SecurityEventBus(ABC):
    """Port for publishing security events to external systems."""

    @abstractmethod
    def publish_authorization_denied(self, event: AuthorizationDeniedEvent) -> None:
        """Publish an authorization denied event."""

    @abstractmethod
    def publish_hitl_event(self, event: HITLEvent) -> None:
        """Publish an HITL event."""

    @abstractmethod
    def publish_policy_decision(self, event: PolicyDecisionEvent) -> None:
        """Publish a policy decision event."""

    @abstractmethod
    def publish_security_exception(self, event: SecurityExceptionEvent) -> None:
        """Publish a security exception event."""


class NoOpSecurityEventBus(SecurityEventBus):
    """Default no-op event bus for when no external integration is configured."""

    def publish_authorization_denied(self, event: AuthorizationDeniedEvent) -> None:
        pass

    def publish_hitl_event(self, event: HITLEvent) -> None:
        pass

    def publish_policy_decision(self, event: PolicyDecisionEvent) -> None:
        pass

    def publish_security_exception(self, event: SecurityExceptionEvent) -> None:
        pass
