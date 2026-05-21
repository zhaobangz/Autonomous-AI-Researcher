import pytest

from config import get_settings


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """Clear get_settings() lru_cache between tests so monkeypatch.setenv() takes effect."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
