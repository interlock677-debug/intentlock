from datetime import UTC, datetime
from uuid import UUID

from app.domain.exceptions.domain_errors import ApprovalRequiredError, AuthorizationError
from app.domain.services.authorization_service import AuthorizationService
from app.domain.value_objects.authorization_context import AuthorizationContext
from app.domain.value_objects.authorization_decision import AuthorizationDecision


def _make_settings(**overrides: object) -> object:
    """Create a simple settings-like object for testing."""
    defaults = {
        "authorization_denied_tools": [],
        "authorization_hitl_tools": [],
        "authorization_require_tenant": False,
        "authorization_allowed_services": None,
        "authorization_allowed_actions": None,
        "authorization_allowed_resources": None,
        "authorization_expiry_seconds": 3600,
    }
    defaults.update(overrides)

    class _Settings:
        pass

    s = _Settings()
    for key, value in defaults.items():
        setattr(s, key, value)
    return s


def _make_context(**overrides: object) -> AuthorizationContext:
    defaults = {
        "user_id": UUID("12345678-1234-5678-1234-567812345678"),
        "agent_id": "agent-1",
        "proposed_tool": "search",
        "tenant_id": None,
        "action": "execute",
        "resource": "",
        "service_id": None,
        "authorized_at": None,
    }
    defaults.update(overrides)
    return AuthorizationContext(**defaults)


def test_authorize_allows_by_default() -> None:
    service = AuthorizationService(settings=_make_settings())
    context = _make_context()
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.ALLOW
    assert reason == "Authorized"


def test_authorize_denies_empty_agent_id() -> None:
    service = AuthorizationService(settings=_make_settings())
    context = _make_context(agent_id="")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing agent identity"


def test_authorize_denies_whitespace_agent_id() -> None:
    service = AuthorizationService(settings=_make_settings())
    context = _make_context(agent_id="   ")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing agent identity"


def test_authorize_denies_missing_user_id() -> None:
    service = AuthorizationService(settings=_make_settings())
    context = _make_context(user_id=None)
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing user identity"


def test_authorize_denies_tool_in_denied_list() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_denied_tools=["dangerous_tool"])
    )
    context = _make_context(proposed_tool="dangerous_tool")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert "dangerous_tool" in reason


def test_authorize_requires_hitl_for_tool_in_hitl_list() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_hitl_tools=["transfer_funds"])
    )
    context = _make_context(proposed_tool="transfer_funds")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.REQUIRE_HITL
    assert "transfer_funds" in reason


def test_authorize_denies_when_tenant_required_and_missing() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_require_tenant=True)
    )
    context = _make_context(tenant_id=None)
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing tenant identity"


def test_authorize_denies_when_tenant_required_and_invalid_empty() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_require_tenant=True)
    )
    context = _make_context(tenant_id="")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing tenant identity"


def test_authorize_denies_when_tenant_required_and_invalid_too_long() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_require_tenant=True)
    )
    context = _make_context(tenant_id="a" * 65)
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Invalid tenant identity"


def test_authorize_allows_when_tenant_required_and_valid() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_require_tenant=True)
    )
    context = _make_context(tenant_id="tenant-abc")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.ALLOW
    assert reason == "Authorized"


def test_authorize_allows_tool_not_in_restricted_lists() -> None:
    service = AuthorizationService(
        settings=_make_settings(
            authorization_denied_tools=["blocked_tool"],
            authorization_hitl_tools=["hitl_tool"],
        )
    )
    context = _make_context(proposed_tool="safe_tool")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.ALLOW
    assert reason == "Authorized"


def test_authorize_decision_order_deny_before_hitl() -> None:
    service = AuthorizationService(
        settings=_make_settings(
            authorization_denied_tools=["blocked_tool"],
            authorization_hitl_tools=["blocked_tool"],
        )
    )
    context = _make_context(proposed_tool="blocked_tool")
    decision, _reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY


def test_authorize_decision_order_tenant_before_agent() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_require_tenant=True)
    )
    context = _make_context(tenant_id=None, agent_id="")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing tenant identity"


def test_authorize_decision_order_agent_before_user() -> None:
    service = AuthorizationService(settings=_make_settings())
    context = _make_context(agent_id="", user_id=None)
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing agent identity"


def test_authorize_decision_order_user_before_tool() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_denied_tools=["blocked_tool"])
    )
    context = _make_context(user_id=None, proposed_tool="blocked_tool")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing user identity"


def test_exception_classes_are_domain_errors() -> None:
    from app.domain.exceptions.domain_errors import (
        DomainError,
    )

    assert issubclass(AuthorizationError, DomainError)
    assert issubclass(ApprovalRequiredError, DomainError)


def test_authorize_denies_when_service_not_allowed() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_allowed_services=["svc-a"])
    )
    context = _make_context(service_id="svc-b")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing or unauthorized service identity"


def test_authorize_allows_when_service_allowed() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_allowed_services=["svc-a"])
    )
    context = _make_context(service_id="svc-a")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.ALLOW
    assert reason == "Authorized"


def test_authorize_denies_missing_service_when_required() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_allowed_services=["svc-a"])
    )
    context = _make_context(service_id=None)
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing or unauthorized service identity"


def test_authorize_denies_when_action_not_allowed() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_allowed_actions=["read"])
    )
    context = _make_context(action="write")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing or unauthorized action"


def test_authorize_allows_when_action_allowed() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_allowed_actions=["read", "write"])
    )
    context = _make_context(action="write")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.ALLOW
    assert reason == "Authorized"


def test_authorize_denies_missing_action_when_required() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_allowed_actions=["read"])
    )
    context = _make_context(action="")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing or unauthorized action"


def test_authorize_denies_when_resource_not_allowed() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_allowed_resources=["doc-a"])
    )
    context = _make_context(resource="doc-b")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing or unauthorized resource"


def test_authorize_allows_when_resource_allowed() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_allowed_resources=["doc-a"])
    )
    context = _make_context(resource="doc-a")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.ALLOW
    assert reason == "Authorized"


def test_authorize_denies_missing_resource_when_required() -> None:
    service = AuthorizationService(
        settings=_make_settings(authorization_allowed_resources=["doc-a"])
    )
    context = _make_context(resource="")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing or unauthorized resource"


def test_authorize_denies_expired_authorization() -> None:
    service = AuthorizationService(settings=_make_settings())
    expired_at = datetime.now(tz=UTC) - __import__("datetime").timedelta(seconds=7200)
    context = _make_context(authorized_at=expired_at)
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Authorization has expired"


def test_authorize_denies_expired_naive_datetime() -> None:
    service = AuthorizationService(settings=_make_settings(authorization_expiry_seconds=10))
    expired_at = datetime.now(tz=UTC) - __import__("datetime").timedelta(seconds=20)
    context = _make_context(authorized_at=expired_at)
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Authorization has expired"


def test_authorize_allows_fresh_authorization() -> None:
    service = AuthorizationService(settings=_make_settings(authorization_expiry_seconds=3600))
    fresh_at = datetime.now(tz=UTC)
    context = _make_context(authorized_at=fresh_at)
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.ALLOW
    assert reason == "Authorized"


def test_authorize_allows_fresh_naive_datetime() -> None:
    service = AuthorizationService(settings=_make_settings(authorization_expiry_seconds=3600))
    fresh_at = datetime.now(UTC).replace(tzinfo=None)
    context = _make_context(authorized_at=fresh_at)
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.ALLOW
    assert reason == "Authorized"


def test_authorize_allows_no_expiration_when_authorized_at_none() -> None:
    service = AuthorizationService(settings=_make_settings())
    context = _make_context(authorized_at=None)
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.ALLOW
    assert reason == "Authorized"


def test_authorize_decision_order_service_before_action() -> None:
    service = AuthorizationService(
        settings=_make_settings(
            authorization_allowed_services=["svc-a"],
            authorization_allowed_actions=["read"],
        )
    )
    context = _make_context(service_id="svc-b", action="read")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing or unauthorized service identity"


def test_authorize_decision_order_action_before_resource() -> None:
    service = AuthorizationService(
        settings=_make_settings(
            authorization_allowed_actions=["read"],
            authorization_allowed_resources=["doc-a"],
        )
    )
    context = _make_context(action="write", resource="doc-a")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing or unauthorized action"


def test_authorize_decision_order_resource_before_tool() -> None:
    service = AuthorizationService(
        settings=_make_settings(
            authorization_allowed_resources=["doc-a"],
            authorization_denied_tools=["dangerous_tool"],
        )
    )
    context = _make_context(resource="doc-b", proposed_tool="dangerous_tool")
    decision, reason = service.authorize(context)
    assert decision == AuthorizationDecision.DENY
    assert reason == "Missing or unauthorized resource"
