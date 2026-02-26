import sys
import os
import types

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "fieldos_test")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret")

sys.modules.setdefault("dotenv", types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None))

from backend.core import config


def test_rejects_missing_jwt(monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", "")
    monkeypatch.setattr(config, "CORS_ORIGINS", ["http://localhost:3000"])

    try:
        config.validate_security_settings()
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "JWT_SECRET" in str(exc)


def test_rejects_wildcard_cors(monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", "a" * 24)
    monkeypatch.setattr(config, "CORS_ORIGINS", ["*"])

    try:
        config.validate_security_settings()
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "CORS_ORIGINS" in str(exc)


def test_production_requires_longer_secret(monkeypatch):
    monkeypatch.setattr(config, "ENVIRONMENT", "production")
    monkeypatch.setattr(config, "JWT_SECRET", "a" * 24)
    monkeypatch.setattr(config, "CORS_ORIGINS", ["https://app.example.com"])

    try:
        config.validate_security_settings()
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "32 chars" in str(exc)


def test_valid_settings_pass(monkeypatch):
    monkeypatch.setattr(config, "ENVIRONMENT", "development")
    monkeypatch.setattr(config, "JWT_SECRET", "a" * 24)
    monkeypatch.setattr(config, "CORS_ORIGINS", ["http://localhost:3000"])

    config.validate_security_settings()
