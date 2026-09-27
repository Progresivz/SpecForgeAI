from pathlib import Path

import pytest

from app.auth.security import create_access_token, validate_password_strength
from app.core.config import Settings
from app.schemas.user import UserCreate


def test_openai_key_is_not_hardcoded():
    source = Path("src/app/core/config.py").read_text(encoding="utf-8")
    assert 'sk-proj-' not in source
    assert Settings(OPENAI_API_KEY="").OPENAI_API_KEY == ""


def test_password_strength_rejects_weak_credentials():
    with pytest.raises(ValueError):
        validate_password_strength("password")
    with pytest.raises(ValueError):
        validate_password_strength("Password")
    with pytest.raises(ValueError):
        validate_password_strength("Password123 ")


def test_password_strength_accepts_application_credentials():
    validate_password_strength("StrongPass123!")
    user = UserCreate(
        username="security_user",
        email="security@example.com",
        password="StrongPass123!",
    )
    assert user.username == "security_user"


def test_user_schema_rejects_weak_password():
    with pytest.raises(ValueError):
        UserCreate(
            username="security_user",
            email="security2@example.com",
            password="password",
        )


def test_production_security_requires_strong_secret():
    config = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="too-short",
        DATABASE_URL="postgresql+psycopg://u:p@db/specforge",
        MIGRATION_MODE="alembic",
        CORS_ORIGINS="https://specforge.example",
        OPENAI_API_KEY="configured",
        GIT_ALLOWED_ROOTS="/data/repos",
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        config.validate_security()


def test_production_security_rejects_insecure_cross_origin_config():
    config = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="strong-production-secret-key-1234567890",
        DATABASE_URL="postgresql+psycopg://u:p@db/specforge",
        MIGRATION_MODE="alembic",
        CORS_ORIGINS="http://example.com",
        OPENAI_API_KEY="configured",
        GIT_ALLOWED_ROOTS="/data/repos",
    )
    with pytest.raises(RuntimeError, match="HTTPS"):
        config.validate_security()


def test_production_security_requires_git_scope_and_ai_secret():
    config = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="strong-production-secret-key-1234567890",
        DATABASE_URL="postgresql+psycopg://u:p@db/specforge",
        MIGRATION_MODE="alembic",
        CORS_ORIGINS="https://specforge.example",
        OPENAI_API_KEY="",
        GIT_ALLOWED_ROOTS="",
    )
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        config.validate_security()


def test_access_tokens_carry_access_type_claim(monkeypatch):
    config = Settings(
        SECRET_KEY="strong-test-secret-key-12345678901234567890",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
    )
    monkeypatch.setattr("app.auth.security.settings", config)
    token = create_access_token({"sub": "test@example.com"})

    from jose import jwt

    payload = jwt.decode(
        token,
        config.SECRET_KEY,
        algorithms=[config.ALGORITHM],
    )
    assert payload["typ"] == "access"
    assert "iat" in payload
    assert "exp" in payload
def test_password_hash_and_verify_round_trip():
    from app.auth.security import hash_password, verify_password

    password = "StrongPass123!"
    hashed = hash_password(password)

    assert hashed
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPass123!", hashed) is False
def test_password_hash_and_verify_round_trip():
    from app.auth.security import hash_password, verify_password

    password = "StrongPass123!"
    hashed = hash_password(password)

    assert hashed
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPass123!", hashed) is False
