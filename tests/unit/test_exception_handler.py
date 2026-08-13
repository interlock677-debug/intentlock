import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.exceptions.domain_errors import (
    ApprovalError,
    AuthenticationError,
    DomainError,
    ExecutionTokenError,
    PolicyViolationError,
    WebhookError,
)
from app.presentation.api.middleware.correlation import CorrelationIdMiddleware
from app.presentation.api.middleware.exception_handler import register_exception_handlers


@pytest.fixture
def app_with_exceptions() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(app)

    @app.get("/raise-auth-error")
    async def raise_auth():
        raise AuthenticationError("Auth error message")

    @app.get("/raise-exec-token-error")
    async def raise_token():
        raise ExecutionTokenError("Token error message")

    @app.get("/raise-policy-error")
    async def raise_policy():
        raise PolicyViolationError("Policy error message")

    @app.get("/raise-webhook-error")
    async def raise_webhook():
        raise WebhookError("Webhook error message")

    @app.get("/raise-approval-error")
    async def raise_approval():
        raise ApprovalError("Approval error message")

    @app.get("/raise-domain-error")
    async def raise_domain():
        raise DomainError("Base domain error")

    @app.get("/raise-unhandled-error")
    async def raise_unhandled():
        raise RuntimeError("Crash unexpected")

    return app


def test_exception_handler_branches(app_with_exceptions: FastAPI) -> None:
    client = TestClient(app_with_exceptions, raise_server_exceptions=False)

    # Auth errors -> 401
    r_auth = client.get("/raise-auth-error")
    assert r_auth.status_code == 401
    assert r_auth.json() == {"detail": "Auth error message"}

    r_token = client.get("/raise-exec-token-error")
    assert r_token.status_code == 401
    assert r_token.json() == {"detail": "Token error message"}

    # Policy / Webhook errors -> 403
    r_policy = client.get("/raise-policy-error")
    assert r_policy.status_code == 403
    assert r_policy.json() == {"detail": "Policy error message"}

    r_webhook = client.get("/raise-webhook-error")
    assert r_webhook.status_code == 403
    assert r_webhook.json() == {"detail": "Webhook error message"}

    # Approval errors -> 404
    r_appr = client.get("/raise-approval-error")
    assert r_appr.status_code == 404
    assert r_appr.json() == {"detail": "Approval error message"}

    # Generic domain error -> 500
    r_dom = client.get("/raise-domain-error")
    assert r_dom.status_code == 500
    assert r_dom.json() == {"detail": "Internal server error."}

    # Unhandled error -> 500 with correlation_id
    r_unh = client.get("/raise-unhandled-error")
    assert r_unh.status_code == 500
    res_data = r_unh.json()
    assert res_data["detail"] == "Internal server error."
    assert "correlation_id" in res_data
