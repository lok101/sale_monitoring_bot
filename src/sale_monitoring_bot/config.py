from __future__ import annotations

from functools import lru_cache
from zoneinfo import ZoneInfo

from beartype import beartype
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from sale_monitoring_bot.env_bootstrap import load_project_env
from sale_monitoring_bot.project_paths import ENV_FILE

load_project_env()

from sale_monitoring_bot.infra.kit_client import KitAPIAccount  # noqa: E402


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    kit_api_login: str
    kit_api_password: SecretStr
    kit_api_company_id: int = Field(gt=0)

    yougile_api_key: SecretStr | None = None
    yougile_chat_id: str | None = None
    yougile_base_url: str = "https://ru.yougile.com/api-v2"
    yougile_login: str | None = None
    yougile_password: SecretStr | None = None
    yougile_company_id: str | None = None

    telegram_bot_token: SecretStr
    telegram_chat_id: str

    days_for_average: int = Field(ge=2)
    sales_drop_percent: int = Field(ge=0, le=100)

    tz: str = "Asia/Yekaterinburg"
    kit_api_tz: str = "Europe/Moscow"
    last_sale_lookup_days: int = Field(default=10, ge=1)
    offline_ping_threshold_minutes: int = Field(default=25, ge=1)

    @field_validator("yougile_base_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def zoneinfo(self) -> ZoneInfo:
        return ZoneInfo(self.tz)

    @property
    def kit_api_zoneinfo(self) -> ZoneInfo:
        return ZoneInfo(self.kit_api_tz)

    @property
    def kit_account(self) -> KitAPIAccount:
        return KitAPIAccount(
            login=self.kit_api_login,
            password=self.kit_api_password.get_secret_value(),
            company_id=self.kit_api_company_id,
        )

    def require_yougile_runtime(self) -> None:
        self.require_yougile_api_key()
        if not self.yougile_chat_id:
            raise ValueError("Не задан YOUGILE_CHAT_ID")

    def require_yougile_api_key(self) -> str:
        if self.yougile_api_key is None:
            raise ValueError("Не задан YOUGILE_API_KEY")
        return self.yougile_api_key.get_secret_value()

    def require_telegram_runtime(self) -> None:
        if self.telegram_bot_token is None:
            raise ValueError("Не задан TELEGRAM_BOT_TOKEN")
        if not self.telegram_chat_id:
            raise ValueError("Не задан TELEGRAM_CHAT_ID")

    def require_yougile_auth(self) -> tuple[str, str, str]:
        if not self.yougile_login:
            raise ValueError("Не задан YOUGILE_LOGIN")
        if self.yougile_password is None:
            raise ValueError("Не задан YOUGILE_PASSWORD")
        if not self.yougile_company_id:
            raise ValueError("Не задан YOUGILE_COMPANY_ID")
        return (
            self.yougile_login,
            self.yougile_password.get_secret_value(),
            self.yougile_company_id,
        )


@beartype
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
