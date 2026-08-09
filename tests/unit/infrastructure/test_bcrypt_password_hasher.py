from app.infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher


def test_hash_and_verify_password() -> None:
    hasher = BcryptPasswordHasher(rounds=4)
    hashed = hasher.hash("SecurePass1!")
    assert hashed != "SecurePass1!"
    assert hasher.verify("SecurePass1!", hashed)


def test_verify_rejects_wrong_password() -> None:
    hasher = BcryptPasswordHasher(rounds=4)
    hashed = hasher.hash("SecurePass1!")
    assert not hasher.verify("WrongPass1!", hashed)
