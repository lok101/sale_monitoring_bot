from __future__ import annotations

from pathlib import Path

# src/sale_monitoring_bot/project_paths.py -> корень репозитория sale_monitoring_bot
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
