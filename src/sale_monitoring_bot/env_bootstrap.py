from __future__ import annotations

from dotenv import load_dotenv

from sale_monitoring_bot.project_paths import ENV_FILE


def load_project_env() -> None:
    """Загрузить .env из корня sale_monitoring_bot до чтения настроек Kit API."""
    if ENV_FILE.is_file():
        load_dotenv(ENV_FILE, override=True)
