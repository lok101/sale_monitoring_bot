from __future__ import annotations

import pytest
from pydantic import ValidationError

from sale_monitoring_bot.config import Settings


def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KIT_API_LOGIN", "u")
    monkeypatch.setenv("KIT_API_PASSWORD", "p")
    monkeypatch.setenv("KIT_API_COMPANY_ID", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    monkeypatch.setenv("DAYS_FOR_AVERAGE", "6")
    monkeypatch.setenv("SALES_DROP_PERCENT", "30")


def test_offline_ping_threshold_minutes_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OFFLINE_PING_THRESHOLD_MINUTES", raising=False)
    _set_required_env(monkeypatch)

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.offline_ping_threshold_minutes == 25


def test_offline_ping_threshold_minutes_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OFFLINE_PING_THRESHOLD_MINUTES", "30")
    _set_required_env(monkeypatch)

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.offline_ping_threshold_minutes == 30


def test_offline_ping_threshold_minutes_rejects_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OFFLINE_PING_THRESHOLD_MINUTES", "0")
    _set_required_env(monkeypatch)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_kit_api_tz_defaults_to_moscow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KIT_API_TZ", raising=False)
    _set_required_env(monkeypatch)

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.kit_api_tz == "Europe/Moscow"
