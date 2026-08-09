from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    """Port for secure password hashing and verification."""

    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, password: str, hashed_password: str) -> bool: ...
