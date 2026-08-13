from fastapi.testclient import TestClient


def test_health_check_includes_security_headers(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_health_check(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_login_and_me_flow(client: TestClient, valid_password: str) -> None:
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": valid_password},
    )
    assert register_response.status_code == 201
    register_body = register_response.json()
    assert register_body["token_type"] == "bearer"
    assert "access_token" in register_body

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": valid_password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "user@example.com"


def test_register_rejects_weak_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "weak"},
    )
    assert response.status_code == 422


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_register_duplicate_email(client: TestClient, valid_password: str) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@example.com", "password": valid_password},
    )
    dup_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@example.com", "password": valid_password},
    )
    assert dup_resp.status_code == 409
    assert "detail" in dup_resp.json()


def test_register_value_error_handling(client: TestClient) -> None:
    from unittest.mock import patch

    with patch(
        "app.presentation.api.v1.routes.auth.RegisterUserUseCase.execute",
        side_effect=ValueError("Invalid field"),
    ):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "valerr@example.com", "password": "Password123!"},
        )
        assert resp.status_code == 422


def test_login_invalid_credentials(client: TestClient, valid_password: str) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": valid_password},
    )
    assert resp.status_code == 401


def test_login_inactive_user_error(client: TestClient) -> None:
    from unittest.mock import patch

    from app.domain.exceptions.domain_errors import InactiveUserError

    with patch(
        "app.presentation.api.v1.routes.auth.AuthenticateUserUseCase.execute",
        side_effect=InactiveUserError("User inactive"),
    ):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@example.com", "password": "Password123!"},
        )
        assert resp.status_code == 401


def test_me_with_nonexistent_user(client: TestClient, valid_password: str) -> None:
    from unittest.mock import patch

    from app.domain.exceptions.domain_errors import UserNotFoundError
    from app.presentation.api.middleware.rate_limit import reset_rate_limits

    reset_rate_limits()
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "ghost@example.com", "password": valid_password},
    )
    token = reg_resp.json()["access_token"]

    with patch(
        "app.application.use_cases.get_current_user.GetCurrentUserUseCase.execute",
        side_effect=UserNotFoundError("User deleted"),
    ):
        resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


