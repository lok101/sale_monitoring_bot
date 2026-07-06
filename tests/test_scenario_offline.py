from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from sale_monitoring_bot.config import Settings
from sale_monitoring_bot.domain.entities import VendingMachineInfo
from sale_monitoring_bot.infra.kit_client import VMStateModel
from sale_monitoring_bot.services.scenario_today import ScenarioTodayService

_TZ = ZoneInfo("Asia/Yekaterinburg")


class _FakeGateway:
    def __init__(self) -> None:
        self.machine = VendingMachineInfo(key="101", name="[101] Кофе", kit_id=1)

    async def get_active_machines(self) -> dict[str, VendingMachineInfo]:
        return {"101": self.machine}

    async def get_vm_states(self) -> list[VMStateModel]:
        return [
            VMStateModel.model_validate(
                {
                    "VendingMachineId": 1,
                    "DateTime": (datetime.now(_TZ) - timedelta(minutes=40)).strftime(
                        "%d.%m.%Y %H:%M:%S"
                    ),
                }
            )
        ]

    async def get_sales(self, from_date: datetime, to_date: datetime) -> list:
        return []


def _settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("KIT_API_LOGIN", "u")
    monkeypatch.setenv("KIT_API_PASSWORD", "p")
    monkeypatch.setenv("KIT_API_COMPANY_ID", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    monkeypatch.setenv("DAYS_FOR_AVERAGE", "6")
    monkeypatch.setenv("SALES_DROP_PERCENT", "30")
    monkeypatch.setenv("OFFLINE_PING_THRESHOLD_MINUTES", "25")
    return Settings(_env_file=None)  # type: ignore[call-arg]


@pytest.mark.asyncio
async def test_scenario_today_includes_offline_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ScenarioTodayService(_settings(monkeypatch), _FakeGateway())
    report = await service.build_report()
    assert len(report.offline_items) == 1
    assert report.offline_items[0].machine.kit_id == 1
