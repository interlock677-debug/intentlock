from enum import StrEnum


class AuthorizationDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_HITL = "require_hitl"
