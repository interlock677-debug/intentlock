from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.application.interfaces.execution_token_service import ExecutionTokenService
from app.application.interfaces.key_manager import KeyManager
from app.application.interfaces.nonce_store import NonceStore
from app.infrastructure.config.settings import Settings, get_settings
from app.infrastructure.redis.client import RedisClient
from app.infrastructure.redis.nonce_store import RedisNonceStore
from app.infrastructure.security.composite_nonce_store import CompositeNonceStore
from app.infrastructure.security.ed25519_execution_token_service import (
    Ed25519ExecutionTokenService,
)
from app.infrastructure.security.env_key_manager import EnvKeyManager
from app.infrastructure.security.memory_nonce_store import MemoryNonceStore


@lru_cache
def get_key_manager() -> KeyManager:
    """Return the appropriate key manager for the environment.

    When ``key_dir`` is configured, ``VersionedKeyManager`` is used for
    persistent versioned Ed25519 keys with rotation support.  Otherwise,
    ``EnvKeyManager`` provides ephemeral or file-backed keys suitable for
    development and test.
    """
    settings = get_settings()
    if settings.key_dir:
        from app.infrastructure.security.versioned_key_manager import VersionedKeyManager

        return VersionedKeyManager(
            key_dir=settings.key_dir,
            jwt_secret=settings.jwt_secret_key,
        )
    return EnvKeyManager(
        jwt_secret=settings.jwt_secret_key,
        execution_key_path=settings.execution_key_path,
    )


@lru_cache
def get_redis_client() -> RedisClient:
    """Return a Redis client (if configured and available).

    Results are cached globally so that the same Redis connection is
    reused across requests.
    """
    settings = get_settings()
    if settings.redis_url and settings.redis_enabled:
        return RedisClient(settings.redis_url)
    return RedisClient(None, enabled=False)


@lru_cache
def get_nonce_store() -> NonceStore:
    """Return the L1 + L2 composite nonce store.

    L1: in-process memory store (fast local replay protection)
    L2: Redis-backed distributed store (cross-instance protection)

    Results are cached globally so that nonce state persists across
    requests within the same application lifecycle.
    """
    redis_client = get_redis_client()
    l1 = MemoryNonceStore()
    if get_settings().app_env == "production" or redis_client.available:
        l2: NonceStore | None = RedisNonceStore(redis_client)
    else:
        l2 = None
    return CompositeNonceStore(l1=l1, l2=l2)


def get_execution_token_service(
    settings: Annotated[Settings, Depends(get_settings)],
    key_manager: Annotated[KeyManager, Depends(get_key_manager)],
    nonce_store: Annotated[NonceStore, Depends(get_nonce_store)],
) -> ExecutionTokenService:
    """Return the Ed25519 execution token service with replay protection."""
    return Ed25519ExecutionTokenService(
        key_manager=key_manager,
        nonce_store=nonce_store,
        clock_skew_seconds=settings.jwt_clock_skew_seconds,
    )


def reset_security_dependencies() -> None:
    """Clear all cached security dependencies.

    Intended for use in test fixtures to ensure isolation between tests.
    """
    get_key_manager.cache_clear()
    get_redis_client.cache_clear()
    get_nonce_store.cache_clear()
