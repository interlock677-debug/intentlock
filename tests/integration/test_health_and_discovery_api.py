from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.presentation.api.dependencies.security import (
    reset_security_dependencies,
)


def test_health_check(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_check_success(client: TestClient) -> None:
    reset_security_dependencies()
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ready", "not_ready")
    assert "db" in data
    assert "redis" in data


def test_readiness_check_db_failure(client: TestClient) -> None:
    with patch(
        "app.presentation.api.v1.routes.health.engine.connect",
        side_effect=Exception("DB Error"),
    ):
        response = client.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["db"] == "unhealthy"


def test_readiness_check_redis_enabled(client: TestClient) -> None:
    with patch("app.presentation.api.v1.routes.health.get_settings") as mock_settings:
        mock_settings.return_value.redis_url = "redis://localhost:6379/0"
        mock_settings.return_value.redis_enabled = True

        with patch("app.presentation.api.v1.routes.health.RedisClient") as mock_redis_cls:
            mock_redis = MagicMock()
            mock_redis.available = True
            mock_redis_cls.return_value = mock_redis

            response = client.get("/api/v1/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["redis"] == "ok"
            assert data["status"] == "ready"

            mock_redis.available = False
            response = client.get("/api/v1/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["redis"] == "unhealthy"
            assert data["status"] == "not_ready"


def test_jwks_discovery(client: TestClient) -> None:
    reset_security_dependencies()
    response = client.get("/api/v1/.well-known/jwks.json")
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert len(data["keys"]) > 0
    assert data["keys"][0]["kty"] == "OKP"
