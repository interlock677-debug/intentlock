from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class User:
    """Core user aggregate root."""

    id: UUID
    email: str
    hashed_password: str
    is_active: bool
    created_at: datetime
