class DomainError(Exception):
    """Base class for domain-level failures."""


class UserNotFoundError(DomainError):
    """Raised when a user cannot be located."""


class DuplicateEmailError(DomainError):
    """Raised when registering with an email that already exists."""


class AuthenticationError(DomainError):
    """Raised when credentials are invalid."""


class InactiveUserError(DomainError):
    """Raised when an inactive user attempts authentication."""


class ExecutionTokenError(DomainError):
    """Raised when an execution token is invalid, expired, or replayed."""


class PolicyViolationError(DomainError):
    """Raised when a policy evaluation blocks an action."""


class ApprovalError(DomainError):
    """Raised when an HITL approval operation fails."""


class WebhookError(DomainError):
    """Raised when a webhook callback fails validation."""
