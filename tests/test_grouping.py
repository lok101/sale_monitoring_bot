from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sale_monitoring_bot.infra.kit_client import KitAPIAccount, KitVendingAPIClient, SaleModel, VMStateModel

from sale_monitoring_bot.domain.entities import VendingMachineInfo
from sale_monitoring_bot.domain.grouping import (
    build_ping_index,
    collect_offline_machines,
    group_sales_by_machine,
    is_offline,
    machine_key,
    sum_sales_by_day,
)

_TZ = ZoneInfo("Asia/Yekaterinburg")


def _sale(
    *,
    vm_id: int,
    name: str,
    price: float,
    dt: datetime,
) -> SaleModel:
    return SaleModel.model_validate(
        {
            "LineNumber": 1,
            "Sum": price,
            "DateTime": dt.strftime("%d.%m.%Y %H:%M:%S"),
            "GoodsName": "1234 | Товар",
            "VendingMachine": vm_id,
            "VendingMachineName": name,
            "MatrixId": None,
        }
    )


def test_machine_key_uses_code() -> None:
    assert machine_key("101", 5) == "101"
    assert machine_key(None, 5) == "id:5"


def test_group_sales_by_machine_code() -> None:
    sales = [
        _sale(
            vm_id=1,
            name="[101] Кофе",
            price=100.0,
            dt=datetime(2026, 5, 20, 10, 0, tzinfo=_TZ),
        ),
        _sale(
            vm_id=2,
            name="[101] Кофе 2",
            price=50.0,
            dt=datetime(2026, 5, 21, 10, 0, tzinfo=_TZ),
        ),
        _sale(
            vm_id=3,
            name="[202] Снек",
            price=30.0,
            dt=datetime(2026, 5, 21, 11, 0, tzinfo=_TZ),
        ),
    ]
    grouped = group_sales_by_machine(sales)
    assert set(grouped.keys()) == {"101", "202"}
    assert len(grouped["101"]) == 2
    assert len(grouped["202"]) == 1


def test_sum_sales_by_day() -> None:
    sales = [
        _sale(
            vm_id=1,
            name="[101] Кофе",
            price=100.0,
            dt=datetime(2026, 5, 25, 10, 0, tzinfo=_TZ),
        ),
        _sale(
            vm_id=1,
            name="[101] Кофе",
            price=40.0,
            dt=datetime(2026, 5, 25, 12, 0, tzinfo=_TZ),
        ),
        _sale(
            vm_id=1,
            name="[101] Кофе",
            price=200.0,
            dt=datetime(2026, 5, 24, 12, 0, tzinfo=_TZ),
        ),
    ]
    total = sum_sales_by_day(sales, datetime(2026, 5, 25, tzinfo=_TZ).date())
    assert total == 140.0


_MACHINE = VendingMachineInfo(key="101", name="[101] Кофе", kit_id=1006360)
_NOW = datetime(2026, 7, 6, 13, 12, 13, tzinfo=_TZ)


def test_is_offline_at_threshold() -> None:
    ping = _NOW - timedelta(minutes=25)
    assert is_offline(ping, _NOW, 25) is True


def test_is_offline_below_threshold() -> None:
    ping = _NOW - timedelta(minutes=24, seconds=59)
    assert is_offline(ping, _NOW, 25) is False


def test_is_offline_when_ping_none() -> None:
    assert is_offline(None, _NOW, 25) is True


def test_build_ping_index() -> None:
    KitVendingAPIClient(
        account=KitAPIAccount(login="u", password="p", company_id=1),
        timezone=ZoneInfo("Europe/Moscow"),
    )
    states = [
        VMStateModel.model_validate(
            {"VendingMachineId": 1, "DateTime": "06.07.2026 12:47:13"}
        ),
        VMStateModel.model_validate({"VendingMachineId": 2, "DateTime": ""}),
    ]
    index = build_ping_index(states)
    assert index[1] == datetime(2026, 7, 6, 12, 47, 13, tzinfo=ZoneInfo("Europe/Moscow"))
    assert index[2] is None


def test_collect_offline_machines_missing_state() -> None:
    machines = {"101": _MACHINE}
    items = collect_offline_machines(machines, {}, _NOW, 25)
    assert len(items) == 1
    assert items[0].last_ping_timestamp is None


def test_collect_offline_machines_sorts_by_name() -> None:
    m_a = VendingMachineInfo(key="101", name="[101] А", kit_id=1)
    m_b = VendingMachineInfo(key="202", name="[202] Б", kit_id=2)
    machines = {"101": m_a, "202": m_b}
    ping_index = {
        1: _NOW - timedelta(minutes=30),
        2: _NOW - timedelta(minutes=5),
    }
    items = collect_offline_machines(machines, ping_index, _NOW, 25)
    assert [i.machine.name for i in items] == ["[101] А"]


def test_is_offline_same_instant_moscow_ping_ekb_now() -> None:
    """Пинг в TZ API (+3) и now в TZ отчёта (+5) — один момент, не offline."""
    moscow = ZoneInfo("Europe/Moscow")
    ekb = ZoneInfo("Asia/Yekaterinburg")
    ping = datetime(2026, 7, 6, 15, 0, tzinfo=moscow)
    now = datetime(2026, 7, 6, 17, 0, tzinfo=ekb)
    assert is_offline(ping, now, 25) is False


def test_is_offline_wrong_tz_makes_recent_ping_look_old() -> None:
    """Если метку API ошибочно привязать к +5 вместо +3 — ложный offline."""
    ekb = ZoneInfo("Asia/Yekaterinburg")
    ping_wrong = datetime(2026, 7, 6, 15, 0, tzinfo=ekb)
    now = datetime(2026, 7, 6, 17, 0, tzinfo=ekb)
    assert is_offline(ping_wrong, now, 25) is True
