from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sale_monitoring_bot.infra.kit_client import SaleModel

from sale_monitoring_bot.domain.grouping import (
    group_sales_by_machine,
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
