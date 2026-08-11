from abc import ABC, abstractmethod


class NonceStore(ABC):
    """Port for atomic nonce consumption to prevent replay attacks."""

    @abstractmethod
    def consume(self, nonce: str, ttl_seconds: int) -> bool:
        """Atomically consume a nonce.

        Returns True if the nonce was successfully consumed (i.e., it was
        not previously used), False if the nonce has already been consumed.
        """

    @abstractmethod
    def is_consumed(self, nonce: str) -> bool:
        """Check whether a nonce has already been consumed."""
