from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain.value_objects.authorization_context import AuthorizationContext
from app.domain.value_objects.authorization_decision import AuthorizationDecision
from app.infrastructure.config.settings import get_settings


class AuthorizationService:
    """Explicit identity-based authorization service.

    Evaluates agent, user, tool, action, resource, service, and tenant
    identities to produce a deterministic ALLOW / DENY / REQUIRE_HITL
    decision.  Defaults are permissive for backward compatibility; production
    deployments should configure explicit restrictions via settings.
    """

    def __init__(self, settings: Any | None = None) -> None:
        self._settings = settings or get_settings()

    def authorize(self, context: AuthorizationContext) -> tuple[AuthorizationDecision, str]:
        """Return an explicit authorization decision and reason.

        The decision is deterministic and auditable.  Checks are ordered
        from most restrictive to least restrictive so that the strongest
        applicable rule wins.
        """
        tenant_decision = self._check_tenant(context)
        if tenant_decision != AuthorizationDecision.ALLOW:
            return tenant_decision, self._tenant_reason(context)

        agent_decision = self._check_agent(context)
        if agent_decision != AuthorizationDecision.ALLOW:
            return agent_decision, self._agent_reason(context)

        user_decision = self._check_user(context)
        if user_decision != AuthorizationDecision.ALLOW:
            return user_decision, self._user_reason(context)

        service_decision = self._check_service(context)
        if service_decision != AuthorizationDecision.ALLOW:
            return service_decision, self._service_reason(context)

        action_decision = self._check_action(context)
        if action_decision != AuthorizationDecision.ALLOW:
            return action_decision, self._action_reason(context)

        resource_decision = self._check_resource(context)
        if resource_decision != AuthorizationDecision.ALLOW:
            return resource_decision, self._resource_reason(context)

        expiration_decision = self._check_expiration(context)
        if expiration_decision != AuthorizationDecision.ALLOW:
            return expiration_decision, self._expiration_reason(context)

        tool_decision = self._check_tool(context)
        if tool_decision != AuthorizationDecision.ALLOW:
            return tool_decision, self._tool_reason(context)

        return AuthorizationDecision.ALLOW, "Authorized"

    def _check_tenant(self, context: AuthorizationContext) -> AuthorizationDecision:
        require_tenant = getattr(self._settings, "authorization_require_tenant", False)
        if not require_tenant:
            return AuthorizationDecision.ALLOW
        if not context.tenant_id:
            return AuthorizationDecision.DENY
        if not self._is_valid_tenant(context.tenant_id):
            return AuthorizationDecision.DENY
        return AuthorizationDecision.ALLOW

    def _check_agent(self, context: AuthorizationContext) -> AuthorizationDecision:
        if not context.agent_id or not str(context.agent_id).strip():
            return AuthorizationDecision.DENY
        return AuthorizationDecision.ALLOW

    def _check_user(self, context: AuthorizationContext) -> AuthorizationDecision:
        if not context.user_id:
            return AuthorizationDecision.DENY
        return AuthorizationDecision.ALLOW

    def _check_service(self, context: AuthorizationContext) -> AuthorizationDecision:
        allowed_services = getattr(self._settings, "authorization_allowed_services", None)
        if allowed_services is not None:
            if not context.service_id:
                return AuthorizationDecision.DENY
            if context.service_id not in allowed_services:
                return AuthorizationDecision.DENY
        return AuthorizationDecision.ALLOW

    def _check_action(self, context: AuthorizationContext) -> AuthorizationDecision:
        allowed_actions = getattr(self._settings, "authorization_allowed_actions", None)
        if allowed_actions is not None:
            if not context.action:
                return AuthorizationDecision.DENY
            if context.action not in allowed_actions:
                return AuthorizationDecision.DENY
        return AuthorizationDecision.ALLOW

    def _check_resource(self, context: AuthorizationContext) -> AuthorizationDecision:
        allowed_resources = getattr(self._settings, "authorization_allowed_resources", None)
        if allowed_resources is not None:
            if not context.resource:
                return AuthorizationDecision.DENY
            if context.resource not in allowed_resources:
                return AuthorizationDecision.DENY
        return AuthorizationDecision.ALLOW

    def _check_expiration(self, context: AuthorizationContext) -> AuthorizationDecision:
        if context.authorized_at is None:
            return AuthorizationDecision.ALLOW
        expiry_seconds = getattr(self._settings, "authorization_expiry_seconds", 3600)
        authorized_at = context.authorized_at
        if authorized_at.tzinfo is None:
            authorized_at = authorized_at.replace(tzinfo=UTC)
        now = datetime.now(tz=UTC)
        if (now - authorized_at).total_seconds() > expiry_seconds:
            return AuthorizationDecision.DENY
        return AuthorizationDecision.ALLOW

    def _check_tool(self, context: AuthorizationContext) -> AuthorizationDecision:
        denied_tools = getattr(self._settings, "authorization_denied_tools", [])
        if context.proposed_tool in denied_tools:
            return AuthorizationDecision.DENY

        hitl_tools = getattr(self._settings, "authorization_hitl_tools", [])
        if context.proposed_tool in hitl_tools:
            return AuthorizationDecision.REQUIRE_HITL

        return AuthorizationDecision.ALLOW

    @staticmethod
    def _is_valid_tenant(tenant_id: str) -> bool:
        return bool(tenant_id and tenant_id.strip() and len(tenant_id) <= 64)

    @staticmethod
    def _tenant_reason(context: AuthorizationContext) -> str:
        if not context.tenant_id:
            return "Missing tenant identity"
        return "Invalid tenant identity"

    @staticmethod
    def _agent_reason(context: AuthorizationContext) -> str:
        return "Missing agent identity"

    @staticmethod
    def _user_reason(context: AuthorizationContext) -> str:
        return "Missing user identity"

    @staticmethod
    def _service_reason(context: AuthorizationContext) -> str:
        return "Missing or unauthorized service identity"

    @staticmethod
    def _action_reason(context: AuthorizationContext) -> str:
        return "Missing or unauthorized action"

    @staticmethod
    def _resource_reason(context: AuthorizationContext) -> str:
        return "Missing or unauthorized resource"

    def _tool_reason(self, context: AuthorizationContext) -> str:
        denied_tools = getattr(self._settings, "authorization_denied_tools", [])
        if context.proposed_tool in denied_tools:
            return f"Tool '{context.proposed_tool}' is denied by authorization policy"
        return f"Tool '{context.proposed_tool}' requires human approval"

    def _expiration_reason(self, context: AuthorizationContext) -> str:
        return "Authorization has expired"
