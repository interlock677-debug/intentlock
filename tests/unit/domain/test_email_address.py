import pytest

from app.domain.value_objects.email_address import EmailAddress


def test_email_address_normalizes_to_lowercase() -> None:
    email = EmailAddress("User@Example.COM")
    assert str(email) == "user@example.com"


def test_email_address_rejects_invalid_format() -> None:
    with pytest.raises(ValueError, match="Invalid email"):
        EmailAddress("not-an-email")
