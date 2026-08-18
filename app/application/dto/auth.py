import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_PASSWORD_MIN_LENGTH = 12
_PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).+$")


class RegisterRequest(BaseModel):
    """Validated registration payload."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=_PASSWORD_MIN_LENGTH, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not _PASSWORD_PATTERN.match(value):
            msg = (
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, one digit, and one special character."
            )
            raise ValueError(msg)
        return value


class LoginRequest(BaseModel):
    """Validated login payload."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    """Public user representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    is_active: bool
    role: str = "viewer"
    tenant_id: str | None = None


class AuthResponse(BaseModel):
    """Authentication result with bearer token."""

    access_token: str
    token_type: str = "bearer"  # noqa: S105
    user: UserResponse
