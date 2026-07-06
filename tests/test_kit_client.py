from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from sale_monitoring_bot.infra.kit_client import KitAPIAccount, KitVendingAPIClient, VMStateModel

_TZ = ZoneInfo("Asia/Yekaterinburg")
_ACCOUNT = KitAPIAccount(login="u", password="p", company_id=1)


def test_vm_state_model_parses_datetime() -> None:
    KitVendingAPIClient(account=_ACCOUNT, timezone=ZoneInfo("Europe/Moscow"))
    model = VMStateModel.model_validate(
        {
            "VendingMachineId": 1006360,
            "DateTime": "06.07.2026 12:47:13",
            "NetworkConnection": 0,
        }
    )
    assert model.id == 1006360
    assert model.last_ping == datetime(2026, 7, 6, 12, 47, 13, tzinfo=ZoneInfo("Europe/Moscow"))


def test_vm_state_model_empty_datetime_is_none() -> None:
    model = VMStateModel.model_validate({"VendingMachineId": 1, "DateTime": ""})
    assert model.last_ping is None


@pytest.mark.asyncio
async def test_get_vm_states_reads_vending_machines_key(monkeypatch: pytest.MonkeyPatch) -> None:
    client = KitVendingAPIClient(account=_ACCOUNT, timezone=_TZ)

    async def _fake_post(
        url: str,
        build_data: Any,
    ) -> dict[str, Any]:
        assert url.endswith("/GetVMStates")
        return {
            "ResultCode": 0,
            "VendingMachines": [
                {"VendingMachineId": 1, "DateTime": "06.07.2026 12:47:13"},
            ],
        }

    monkeypatch.setattr(client, "_post", _fake_post)
    states = await client.get_vm_states()
    assert len(states) == 1
    assert states[0].id == 1
    await client.close()
