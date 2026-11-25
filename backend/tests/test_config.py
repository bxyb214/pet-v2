"""生产启动校验：默认/过短的 JWT secret 必须拒绝。"""
import pytest

from app.core.config import Settings, require_production_secret


def _settings(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


def test_dev_mode_allows_default_secret():
    require_production_secret(_settings(dev_mode=True))


def test_prod_rejects_default_or_short_secret():
    with pytest.raises(RuntimeError):
        require_production_secret(_settings(dev_mode=False, jwt_secret="dev-only-change-me"))
    with pytest.raises(RuntimeError):
        require_production_secret(_settings(dev_mode=False, jwt_secret="short"))


def test_prod_accepts_strong_secret():
    require_production_secret(_settings(dev_mode=False, jwt_secret="x" * 32))
