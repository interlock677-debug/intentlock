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
