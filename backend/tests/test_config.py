import importlib.util
from pathlib import Path

import dotenv
import pytest

CONFIG_PATH = Path(__file__).resolve().parents[1] / "app" / "core" / "config.py"


def _load_config_module(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, CONFIG_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_settings_raises_when_jwt_secret_is_missing(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost")
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: True)

    with pytest.raises(RuntimeError, match="JWT_SECRET must be set in environment"):
        _load_config_module("config_missing_jwt")


def test_settings_normalizes_invalid_cookie_samesite_to_lax(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("COOKIE_SAMESITE", "invalid-value")
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost")
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: True)

    config_mod = _load_config_module("config_invalid_samesite")
    assert config_mod.settings.COOKIE_SAMESITE == "lax"
