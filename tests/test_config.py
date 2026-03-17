import pytest

from wellnessbox_rnd.config import Settings


def test_settings_accept_provider_env_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WB_RND_ENV", "staging")
    monkeypatch.setenv("PORT", "8010")
    monkeypatch.setenv("WEB_CONCURRENCY", "1")

    settings = Settings(_env_file=None)

    assert settings.app_env == "staging"
    assert settings.port == 8010
    assert settings.workers == 1


def test_settings_reject_invalid_api_prefix() -> None:
    with pytest.raises(ValueError, match="api_prefix_must_start_with_slash"):
        Settings(api_prefix="v1", _env_file=None)
