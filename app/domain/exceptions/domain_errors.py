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


class TokenSubjectMismatchError(DomainError):
    """Raised when an execution token subject does not match the caller."""


class PolicyViolationError(DomainError):
    """Raised when a policy evaluation blocks an action."""


class ApprovalError(DomainError):
    """Raised when an HITL approval operation fails."""


class AuthorizationError(DomainError):
    """Raised when an action is denied by the authorization service."""


class ApprovalRequiredError(DomainError):
    """Raised when an action requires human approval before proceeding."""


class WebhookError(DomainError):
    """Raised when a webhook callback fails validation."""
